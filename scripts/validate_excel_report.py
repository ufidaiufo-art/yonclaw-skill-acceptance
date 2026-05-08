#!/usr/bin/env python3
"""Validate final YonClaw Excel acceptance reports.

Dependency-free by design: parses .xlsx as zip/xml so the gate can run even
when openpyxl is unavailable in the YonClaw runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


NS_MAIN = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
NS_OFFICE_REL = {"r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}

SUMMARY_HEADERS = ("技能清单", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率")
SKILL_SUMMARY_HEADERS = ("项目", "测试点总数", "验证通过", "验证不通过", "未执行", "通过率")
DETAIL_HEADERS = ("方法论大项", "具体测试点", "测试结果", "备注")
CHECK_HEADERS = ("检查点ID", "方法论大项", "检查点", "适用性", "覆盖位置", "自检结果", "备注")

VALID_DETAIL_RESULTS = {"通过", "不通过", "未执行"}
VALID_CHECK_RESULTS = {"通过", "未通过", "阻塞", "不适用"}
GENERIC_LOCATIONS = {"已覆盖", "见报告", "见摘要", "报告中", "详见报告"}
NOT_APPLICABLE_VALUES = {"不适用", "否", "N/A", "NA", "not_applicable"}
REPORT_SELF_CHECK_KEYWORDS = (
    "Excel 文件已生成",
    "Excel 路径",
    "默认输出 Excel",
    "公式错误扫描",
    "检查点自检",
    "只输出一份汇总报告",
)


@dataclass
class Result:
    ok: bool
    errors: list[str]
    warnings: list[str]


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _load_json(path: Path | None, errors: list[str]) -> dict[str, Any] | None:
    if path is None:
        return None
    if not path.exists():
        errors.append(f"missing checkpoints artifact: {path}")
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid checkpoints JSON {path}: {exc}")
        return None
    if not isinstance(data, dict):
        errors.append(f"checkpoints JSON must be an object: {path}")
        return None
    return data


def _read_xml(zf: zipfile.ZipFile, name: str) -> ET.Element:
    return ET.fromstring(zf.read(name))


def _shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = _read_xml(zf, "xl/sharedStrings.xml")
    values: list[str] = []
    for si in root.findall("x:si", NS_MAIN):
        texts = [node.text or "" for node in si.iter() if _local(node.tag) == "t"]
        values.append("".join(texts))
    return values


def _sheet_targets(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = _read_xml(zf, "xl/workbook.xml")
    rels = _read_xml(zf, "xl/_rels/workbook.xml.rels")
    rel_map: dict[str, str] = {}
    for rel in rels:
        rel_id = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")
        if rel_id:
            if not target.startswith("/"):
                target = "xl/" + target
            rel_map[rel_id] = target.lstrip("/")

    targets: dict[str, str] = {}
    for sheet in workbook.findall(".//x:sheet", NS_MAIN):
        name = sheet.attrib.get("name", "")
        rel_id = sheet.attrib.get(f"{{{NS_OFFICE_REL['r']}}}id")
        if name and rel_id and rel_id in rel_map:
            targets[name] = rel_map[rel_id]
    return targets


def _column_index(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha())
    result = 0
    for ch in letters:
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
    return max(result - 1, 0)


def _cell_text(cell: ET.Element, shared: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        texts = [node.text or "" for node in cell.iter() if _local(node.tag) == "t"]
        return "".join(texts).strip()
    value = cell.find("x:v", NS_MAIN)
    raw = "" if value is None or value.text is None else value.text
    if cell_type == "s":
        try:
            return shared[int(raw)].strip()
        except (ValueError, IndexError):
            return raw.strip()
    return raw.strip()


def _sheet_rows(zf: zipfile.ZipFile, target: str, shared: list[str]) -> list[list[str]]:
    root = _read_xml(zf, target)
    rows: list[list[str]] = []
    for row in root.findall(".//x:row", NS_MAIN):
        values: list[str] = []
        for cell in row.findall("x:c", NS_MAIN):
            index = _column_index(cell.attrib.get("r", ""))
            while len(values) <= index:
                values.append("")
            values[index] = _cell_text(cell, shared)
        while values and values[-1] == "":
            values.pop()
        rows.append(values)
    return rows


def _workbook_rows(path: Path, errors: list[str]) -> dict[str, list[list[str]]]:
    if not path.exists():
        errors.append(f"missing report: {path}")
        return {}
    if path.suffix.lower() != ".xlsx":
        errors.append(f"report extension must be .xlsx: {path.name}")
    if path.stat().st_size <= 0:
        errors.append(f"report is empty: {path}")
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile:
        errors.append("report is not a readable xlsx/zip archive")
        return {}

    with zf:
        try:
            shared = _shared_strings(zf)
            targets = _sheet_targets(zf)
            return {name: _sheet_rows(zf, target, shared) for name, target in targets.items()}
        except Exception as exc:  # pragma: no cover - defensive parse failure
            errors.append(f"failed to parse workbook: {exc}")
            return {}


def _find_header(rows: list[list[str]], headers: tuple[str, ...]) -> int | None:
    for index, row in enumerate(rows):
        if tuple(row[: len(headers)]) == headers:
            return index
    return None


def _data_rows(rows: list[list[str]], header_index: int, min_cols: int) -> list[tuple[int, list[str]]]:
    output: list[tuple[int, list[str]]] = []
    for offset, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any(row):
            continue
        output.append((offset, row + [""] * max(0, min_cols - len(row))))
    return output


def _to_int(value: str) -> int | None:
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _coverage_target(location: str) -> tuple[str, int | None] | None:
    if not location or location == "未覆盖" or location in GENERIC_LOCATIONS:
        return None
    # Accept "sheet!B12", "sheet!12", "sheet row 12", and plain sheet names.
    match = re.search(r"^(.+?)![A-Z]*([0-9]+)$", location)
    if match:
        return match.group(1), int(match.group(2))
    match = re.search(r"^(.+?)\s*(?:row|行)\s*([0-9]+)$", location, re.I)
    if match:
        return match.group(1), int(match.group(2))
    return location, None


def _checkpoint_ids(data: dict[str, Any] | None) -> set[str]:
    if not data:
        return set()
    checkpoints = data.get("checkpoints")
    if not isinstance(checkpoints, list):
        return set()
    return {str(item.get("id")) for item in checkpoints if isinstance(item, dict) and item.get("id")}


def validate(report: Path, checkpoints: Path | None = None) -> Result:
    errors: list[str] = []
    warnings: list[str] = []
    checkpoint_data = _load_json(checkpoints, errors)
    expected_checkpoint_ids = _checkpoint_ids(checkpoint_data)
    sheets = _workbook_rows(report, errors)
    if errors and not sheets:
        return Result(False, errors, warnings)

    if "汇总" not in sheets:
        errors.append("missing required sheet: 汇总")
    if "检查点自检" not in sheets:
        errors.append("missing required sheet: 检查点自检")

    detail_sheets = [
        name for name in sheets
        if name not in {"汇总", "检查点自检"} and not name.endswith("汇总")
    ]
    if not detail_sheets:
        errors.append("missing target skill detail sheet")

    detail_stats: dict[str, tuple[Counter[str], dict[str, Counter[str]]]] = {}
    for sheet_name in detail_sheets:
        rows = sheets[sheet_name]
        header_index = _find_header(rows, DETAIL_HEADERS)
        if header_index is None:
            errors.append(f"{sheet_name}: missing headers {DETAIL_HEADERS}")
            continue
        total = Counter()
        by_category: dict[str, Counter[str]] = defaultdict(Counter)
        for excel_row, row in _data_rows(rows, header_index, len(DETAIL_HEADERS)):
            category, point, result, note = row[:4]
            if result not in VALID_DETAIL_RESULTS:
                errors.append(f"{sheet_name}!row {excel_row}: invalid test result {result!r}")
                continue
            if any(keyword in " ".join(row) for keyword in REPORT_SELF_CHECK_KEYWORDS):
                errors.append(f"{sheet_name}!row {excel_row}: report self-check item appears in target detail sheet")
            total[result] += 1
            by_category[category][result] += 1
        detail_stats[sheet_name] = (total, by_category)

    if "汇总" in sheets:
        rows = sheets["汇总"]
        header_index = _find_header(rows, SUMMARY_HEADERS)
        if header_index is None:
            errors.append(f"汇总: missing headers {SUMMARY_HEADERS}")
        else:
            summary = {row[0]: row for _, row in _data_rows(rows, header_index, len(SUMMARY_HEADERS))}
            for skill_name, (total, _by_category) in detail_stats.items():
                row = summary.get(skill_name)
                if row is None:
                    errors.append(f"汇总: missing skill row {skill_name}")
                    continue
                expected = (sum(total.values()), total["通过"], total["不通过"], total["未执行"])
                actual = (_to_int(row[1]), _to_int(row[2]), _to_int(row[3]), _to_int(row[4]))
                if actual != expected:
                    errors.append(f"汇总/{skill_name}: expected total/pass/fail/unexecuted={expected}, actual={actual}")

    for skill_name, (total, by_category) in detail_stats.items():
        summary_name = f"{skill_name}汇总"
        if summary_name not in sheets:
            errors.append(f"missing skill summary sheet: {summary_name}")
            continue
        header_index = _find_header(sheets[summary_name], SKILL_SUMMARY_HEADERS)
        if header_index is None:
            errors.append(f"{summary_name}: missing headers {SKILL_SUMMARY_HEADERS}")
            continue
        summary = {row[0]: row for _, row in _data_rows(sheets[summary_name], header_index, len(SKILL_SUMMARY_HEADERS))}
        for category, counts in by_category.items():
            row = summary.get(category)
            if row is None:
                errors.append(f"{summary_name}: missing category row {category}")
                continue
            expected = (sum(counts.values()), counts["通过"], counts["不通过"], counts["未执行"])
            actual = (_to_int(row[1]), _to_int(row[2]), _to_int(row[3]), _to_int(row[4]))
            if actual != expected:
                errors.append(f"{summary_name}/{category}: expected total/pass/fail/unexecuted={expected}, actual={actual}")
        if total["不通过"] or total["未执行"]:
            warnings.append(f"{skill_name}: contains fail/unexecuted detail rows; final verdict must be downgraded or justified")

    if "检查点自检" in sheets:
        rows = sheets["检查点自检"]
        header_index = _find_header(rows, CHECK_HEADERS)
        if header_index is None:
            errors.append(f"检查点自检: missing headers {CHECK_HEADERS}")
        else:
            seen_ids: set[str] = set()
            for excel_row, row in _data_rows(rows, header_index, len(CHECK_HEADERS)):
                checkpoint_id, _category, _point, applicability, location, result, note = row[:7]
                if not checkpoint_id:
                    errors.append(f"检查点自检!row {excel_row}: missing checkpoint ID")
                    continue
                seen_ids.add(checkpoint_id)
                if result not in VALID_CHECK_RESULTS:
                    errors.append(f"检查点自检!row {excel_row}: invalid self-check result {result!r}")
                if result in {"未通过", "阻塞"} and not note:
                    errors.append(f"检查点自检!row {excel_row}: failing/blocking checkpoint must include note")
                if applicability not in NOT_APPLICABLE_VALUES:
                    if not location:
                        errors.append(f"检查点自检!row {excel_row}: coverage location is empty")
                    elif location in VALID_CHECK_RESULTS:
                        errors.append(
                            f"检查点自检!row {excel_row}: coverage location looks like a self-check result, "
                            f"expected concrete location such as <skill-name>!B12 or 未覆盖: {location}"
                        )
                    elif location in GENERIC_LOCATIONS:
                        errors.append(f"检查点自检!row {excel_row}: coverage location is too generic: {location}")
                    elif location != "未覆盖":
                        target = _coverage_target(location)
                        if target is None:
                            errors.append(f"检查点自检!row {excel_row}: invalid coverage location {location!r}")
                        else:
                            sheet_name, row_number = target
                            if sheet_name not in sheets:
                                errors.append(f"检查点自检!row {excel_row}: coverage sheet not found: {sheet_name}")
                            elif row_number is not None and row_number > len(sheets[sheet_name]):
                                errors.append(f"检查点自检!row {excel_row}: coverage row out of range: {location}")

            if expected_checkpoint_ids:
                missing = sorted(expected_checkpoint_ids - seen_ids)
                if missing:
                    errors.append(f"检查点自检: missing checkpoint IDs from checkpoints-covered.json: {', '.join(missing)}")

    return Result(not errors, errors, warnings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final YonClaw Excel acceptance report.")
    parser.add_argument("report", type=Path)
    parser.add_argument("--checkpoints", type=Path, help="Path to checkpoints-covered.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = validate(args.report, args.checkpoints)
    if args.json:
        print(json.dumps({"ok": result.ok, "errors": result.errors, "warnings": result.warnings}, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result.ok else "FAIL")
        for error in result.errors:
            print(f"ERROR: {error}")
        for warning in result.warnings:
            print(f"WARN: {warning}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
