#!/usr/bin/env python3
"""Validate YonClaw enterprise acceptance reports.

The validator intentionally checks deterministic contradictions that an LLM
can miss while writing the report narrative.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_SECTIONS = (
    "### 8.3 异常输入与副作用审计",
    "### 9.1 功能清单与 Action Inventory",
    "### 9.2 覆盖矩阵",
    "### 9.3 动态用例结果",
    "### 9.4 功能覆盖结论",
    "### 10.4 结论一致性自检",
    "#### 10.4.1 结论矛盾校验",
    "### 10.5 验收结论",
    "### 10.6 发布建议",
)

FEATURE_ID_RE = r"\bF-?\d+\b"


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]
    error_codes: list[str]


def _checked_value(section: str, label: str) -> str | None:
    pattern = re.compile(
        rf"{re.escape(label)}.*?(?=\n####|\n###|\n##|\Z)",
        flags=re.S,
    )
    match = pattern.search(section)
    if not match:
        return None
    block = match.group(0)
    checked = re.search(r"- \[x\]\s*([^\n]+)", block)
    return checked.group(1).strip() if checked else None


def _clean_cell(value: str) -> str:
    return re.sub(r"[`*_✅❌⚠️✔✘]", "", value).strip()


def _is_pass(value: str | None) -> bool:
    if not value:
        return False
    clean = _clean_cell(value)
    return "通过" in clean and "有条件通过" not in clean and "不通过" not in clean


def _is_conditional(value: str | None) -> bool:
    return bool(value and "有条件通过" in _clean_cell(value))


def _is_internal_release(value: str | None) -> bool:
    if not value:
        return False
    clean = _clean_cell(value)
    return "适合 YonClaw 内部发布" in clean or "适合内部发布" in clean


def _table_value(section: str, label: str) -> str | None:
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] == label:
            return cells[1]
    return None


def _verdict_value(section: str, label: str) -> str | None:
    return _checked_value(section, label) or _table_value(section, label)


def _table_has_headers(section: str, required_headers: tuple[str, ...]) -> bool:
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        return all(any(required == cell for cell in cells) for required in required_headers)
    return False


def _section_has_table_rows(section: str, required_labels: tuple[str, ...]) -> bool:
    labels: set[str] = set()
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if cells:
            labels.add(cells[0])
    return all(label in labels for label in required_labels)


def _markdown_table_rows(section: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in section.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in line.strip().strip("|").split("|")]
        if not cells or all(set(cell) <= {"-"} for cell in cells):
            continue
        rows.append(cells)
    return rows


def _feature_categories(text: str) -> dict[str, str]:
    inventory = _section(text, "### 9.1 功能清单与 Action Inventory", end_pattern=r"\n### 9\.2|\n## ")
    categories: dict[str, str] = {}
    for row in _markdown_table_rows(inventory):
        if row and row[0] == "Feature ID":
            continue
        if len(row) >= 3 and re.search(FEATURE_ID_RE, row[0]):
            categories[re.search(FEATURE_ID_RE, row[0]).group(0)] = row[2]
    return categories


def _coverage_rows(text: str) -> list[dict[str, str]]:
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for row in _markdown_table_rows(coverage):
        if row and row[0] == "Feature ID":
            headers = row
            continue
        if not headers or len(row) < len(headers):
            continue
        item = {headers[index]: row[index] for index in range(len(headers))}
        feature_match = re.search(FEATURE_ID_RE, item.get("Feature ID", ""))
        if feature_match:
            item["feature_id"] = feature_match.group(0)
        rows.append(item)
    return rows


def _api_mapping_rows(text: str) -> list[dict[str, str]]:
    api_section = _section(text, "### 9.3a API/端点映射表", end_pattern=r"\n### 9\.4|\n## ")
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for row in _markdown_table_rows(api_section):
        if row and row[0] == "Action":
            headers = row
            continue
        if not headers or len(row) < len(headers):
            continue
        rows.append({headers[index]: row[index] for index in range(len(headers))})
    return rows


def _section(text: str, start: str, end_pattern: str = r"\n## ") -> str:
    index = text.find(start)
    if index < 0:
        return ""
    tail = text[index:]
    end = re.search(end_pattern, tail[len(start) :])
    if not end:
        return tail
    return tail[: len(start) + end.start()]


def _has_platform_pending(text: str) -> bool:
    return bool(
        re.search(r"跨平台[^\n]*(pending|未验证|仅\s*macOS|Windows\s*未知|需\s*Windows|platform-max-conditional)", text, re.I)
        or re.search(r"platform-max-conditional", text, re.I)
    )


def _has_safety_pending(text: str) -> bool:
    return bool(
        re.search(r"Safety[^|\n]*(pending|未执行|未完成|business-max-conditional)", text, re.I)
        or re.search(r"business-max-conditional", text, re.I)
    )


def _has_pending_or_static_gap(text: str) -> bool:
    return bool(re.search(r"\b(pending|static-only|blocked|skipped)\b|待补验证|未动态验证|未执行", text, re.I))


def _has_internal_release_adaptation_conflict(text: str, release: str | None) -> bool:
    if release is None or _is_internal_release(release):
        return False
    for line in text.splitlines():
        if "内部发布适配" not in line:
            continue
        if "适合内部发布" in line or "适合 YonClaw 内部发布" in line:
            return True
    return False


def _has_write_covered_by_incomplete_input_only(text: str) -> bool:
    inventory = _section(text, "### 9.1 功能清单与 Action Inventory", end_pattern=r"\n### 9\.2|\n## ")
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    dynamic_cases = _section(text, "### 9.3 动态用例结果", end_pattern=r"\n### 9\.3a|\n### 9\.4|\n## ")
    if not coverage or not dynamic_cases:
        return False

    write_action_patterns = (
        r"create_[a-z0-9_]*",
        r"update_[a-z0-9_]*",
        r"delete_[a-z0-9_]*",
        r"cancel_[a-z0-9_]*",
        r"invite_[a-z0-9_]*",
        r"send_[a-z0-9_]*",
        r"submit_[a-z0-9_]*",
        r"restart_[a-z0-9_]*",
    )
    write_action_re = re.compile("|".join(write_action_patterns), re.I)
    incomplete_re = re.compile(r"缺参|缺\s*confirm|无参数|Incomplete Input|success:false|success=false", re.I)
    write_feature_ids: set[str] = set()

    for line in inventory.splitlines():
        feature_match = re.search(FEATURE_ID_RE, line)
        if not feature_match:
            continue
        if "WRITE" in line or write_action_re.search(line):
            write_feature_ids.add(feature_match.group(0))

    for line in coverage.splitlines():
        feature_match = re.search(FEATURE_ID_RE, line)
        is_write_feature = bool(feature_match and feature_match.group(0) in write_feature_ids)
        if "covered" not in line.lower() or not (is_write_feature or write_action_re.search(line)):
            continue
        if incomplete_re.search(line):
            return True
        case_ids = re.findall(r"\bTC-\d+\b", line)
        if case_ids and all(
            re.search(rf"\b{case_id}\b[^\n]*(缺参|缺\s*confirm|无参数|Incomplete Input|success:false|success=false)", dynamic_cases, re.I)
            for case_id in case_ids
        ):
            return True
    return False


def _has_key_feature_gap(text: str) -> bool:
    inventory = _section(text, "### 9.1 功能清单与 Action Inventory", end_pattern=r"\n### 9\.2|\n## ")
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    if not inventory or not coverage:
        return False

    key_feature_ids: set[str] = set()
    for line in inventory.splitlines():
        feature_match = re.search(FEATURE_ID_RE, line)
        if not feature_match:
            continue
        if re.search(r"\b(WRITE|STATE|SPECIAL)\b", line):
            key_feature_ids.add(feature_match.group(0))

    gap_re = re.compile(r"\b(static-only|pending|blocked|skipped|guardrail-only)\b", re.I)
    for line in coverage.splitlines():
        feature_match = re.search(FEATURE_ID_RE, line)
        if feature_match and feature_match.group(0) in key_feature_ids and gap_re.search(line):
            return True
    return False


def _has_verdict_text_conflict(text: str, business: str | None, platform: str | None) -> tuple[bool, bool]:
    tail = _section(text, "### 10.5 验收结论", end_pattern=r"\Z")
    business_conflict = bool(
        _is_conditional(business)
        and re.search(r"业务能力结论[：:]\s*通过|业务能力[^。\n]*符合[^。\n]*发布要求", tail)
    )
    platform_conflict = bool(
        _is_conditional(platform)
        and re.search(r"平台集成结论[：:]\s*通过|平台集成[^。\n]*符合[^。\n]*发布要求", tail)
    )
    return business_conflict, platform_conflict


def _has_unexecuted_executable_feature(text: str) -> bool:
    inventory = _section(text, "### 9.1 功能清单与 Action Inventory", end_pattern=r"\n### 9\.2|\n## ")
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    if not coverage:
        return False

    executable_feature_ids: set[str] = set()
    for line in inventory.splitlines():
        feature_match = re.search(FEATURE_ID_RE, line)
        if not feature_match:
            continue
        if re.search(r"\b(READ|WRITE|STATE|SPECIAL)\b", line):
            executable_feature_ids.add(feature_match.group(0))

    executable_re = re.compile(r"\b(prompt-dynamic|script-api|pytest)\b", re.I)
    unexecuted_re = re.compile(r"\b(pending|static-only)\b|未验证|仅静态", re.I)
    allowed_reason_re = re.compile(
        r"out-of-scope|用户明确缩小范围|用户指定不执行|用户未确认|需确认|需要确认|高风险未获确认|不可逆|无法回滚|生产污染风险|无法安全执行",
        re.I,
    )

    for line in coverage.splitlines():
        if not line.strip().startswith("|") or "Feature ID" in line:
            continue
        feature_match = re.search(FEATURE_ID_RE, line)
        is_executable_feature = bool(feature_match and feature_match.group(0) in executable_feature_ids)
        if (executable_re.search(line) or is_executable_feature) and unexecuted_re.search(line) and not allowed_reason_re.search(line):
            return True
    return False


def _has_prepared_environment_skip(text: str) -> bool:
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    if not coverage:
        return False
    invalid_reason_re = re.compile(
        r"无测试环境|无环境|缺少测试环境|环境未准备|无权限|缺少权限|未授权|认证失败|平台阻塞|环境阻塞|后续补充|后续补测",
        re.I,
    )
    return bool(invalid_reason_re.search(coverage))


def _has_unsupported_scope_reduction(text: str) -> bool:
    if "用户明确缩小范围" not in text:
        return False
    evidence_re = re.compile(
        r"(用户明确缩小范围证据|用户原话|用户指令|范围收缩证据)\s*[：:]\s*(?!\s*(无|N/A|pending|未记录))",
        re.I,
    )
    return not bool(evidence_re.search(text))


def _coverage_fractions(text: str) -> set[tuple[int, int]]:
    fractions: set[tuple[int, int]] = set()
    patterns = (
        r"动态覆盖率摘要\s*\|[^|\n]*(\d+)\s*/\s*(\d+)",
        r"动态覆盖率\**\s*[：:]\s*(\d+)\s*/\s*(\d+)",
        r"已动态覆盖\s*\|\s*(\d+)\s*/\s*(\d+)",
        r"动态覆盖[^|\n]*(\d+)\s*个动态覆盖[^|\n]*(\d+)\s*个静态覆盖",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            first, second = int(match.group(1)), int(match.group(2))
            if "个静态覆盖" in match.group(0):
                fractions.add((first, first + second))
            else:
                fractions.add((first, second))
    return fractions


def _has_coverage_count_conflict(text: str) -> bool:
    return len(_coverage_fractions(text)) > 1


def _has_release_recommendation_conflict(text: str, release: str | None) -> bool:
    if release is None or _is_internal_release(release):
        return False
    final_section = _section(text, "### 10.5 验收结论", end_pattern=r"\Z")
    before_final = text.replace(final_section, "")
    return bool(re.search(r"适合\s*(YonClaw\s*)?内部发布|适合发布|可发布|满足.*发布", before_final))


def _has_safety_static_only_pass(text: str) -> bool:
    static_evidence_re = re.compile(r"Safety[^\n|]*\|[^\n]*(PASS|通过|✅)[^\n]*(静态|规则|阅读|加载|触发确认)", re.I)
    if static_evidence_re.search(text):
        return True
    dynamic_cases = _section(text, "### 9.3 动态用例结果", end_pattern=r"\n### 9\.3a|\n### 9\.4|\n## ")
    safety_pass_re = re.compile(r"Safety[^\n]*(PASS|通过|✅)", re.I)
    dynamic_evidence_re = re.compile(r"Safety[^\n]*(prompt|session|run-|TC-|真实|拒绝|用户请求)", re.I)
    return bool(safety_pass_re.search(text) and not dynamic_evidence_re.search(dynamic_cases))


def _has_open_gaps_marked_none(text: str) -> bool:
    if not _has_pending_or_static_gap(text):
        return False
    none_patterns = (
        r"关键未决项\s*\|\s*无\s*\|",
        r"关键未决项[：:]\s*无",
        r"未覆盖\**\s*[：:]\s*无",
    )
    return any(re.search(pattern, text) for pattern in none_patterns)


def _has_section_numbering_conflict(text: str) -> bool:
    headings = re.findall(r"^(#{3,4})\s+([0-9]+(?:\.[0-9]+)*)\s+(.+)$", text, flags=re.M)
    top_level: dict[str, list[str]] = {}
    for hashes, number, title in headings:
        if hashes == "###":
            top_level.setdefault(number, []).append(title.strip())

    if any(len(titles) > 1 for titles in top_level.values()):
        return True
    if "10.4.3" in text:
        return True
    if "### 10.5 发布建议" in text:
        return True
    return False


def _has_auto_validation_not_recorded(text: str) -> bool:
    section = _section(text, "### 11.3 自动合规校验", end_pattern=r"\n## ")
    if not section:
        return False
    return bool(
        re.search(r"结果\s*\|\s*(待执行|pending|N/A|未执行|未记录|<pass-or-fail>)", section, re.I)
        or re.search(r"(?:\*\*)?(?:校验)?结果(?:\*\*)?\s*[：:]\s*(待执行|pending|N/A|未执行|未记录|<pass-or-fail>)", section, re.I)
    )


def _has_auto_validation_final_fail(text: str) -> bool:
    section = _section(text, "### 11.3 自动合规校验", end_pattern=r"\n## ")
    if not section:
        return False
    result = _table_value(section, "结果")
    return bool(result and re.search(r"\bFAIL\b|失败", result, re.I))


def _has_auto_validation_self_check_na(text: str) -> bool:
    self_check = _section(text, "#### 10.4.1 结论矛盾校验", end_pattern=r"\n### |\n## ")
    for line in self_check.splitlines():
        if "validate_report.py" in line or "校验器" in line or "自动合规" in line:
            if re.search(r"N/A|未运行|不适用|无法运行", line, re.I):
                return True
    return False


def _has_auto_validation_self_check_pending(text: str) -> bool:
    self_check = _section(text, "#### 10.4.1 结论矛盾校验", end_pattern=r"\n### |\n## ")
    pending_re = re.compile(r"待运行|需运行|需要运行|待重新校验|需重新运行|模板待运行|待执行|未完成", re.I)
    for line in self_check.splitlines():
        if "validate_report.py" in line or "校验器" in line or "自动合规" in line:
            if pending_re.search(line):
                return True
    return False


def _has_auto_validation_stale_failure_items(text: str) -> bool:
    section = _section(text, "### 11.3 自动合规校验", end_pattern=r"\n## ")
    if not section:
        return False
    result = _table_value(section, "结果") or ""
    failures = _table_value(section, "失败项") or ""
    if re.search(r"\bFAIL\b|失败", result, re.I):
        return False
    if not failures:
        return False
    if re.fullmatch(r"\s*(无|none|no errors?|0|N/A|-)\s*", failures, flags=re.I):
        return False
    return bool(
        re.search(
            r"\b[a-z][a-z0-9-]+(?:-[a-z0-9]+)+\b|ERROR|FAIL|失败|旧失败|首次运行失败",
            failures,
            re.I,
        )
    )


def _has_summary_missing_gate_pending(text: str) -> bool:
    summary = _section(text, "## 0. 执行摘要", end_pattern=r"\n## ")
    if not summary:
        return False
    unresolved = _table_value(summary, "关键未决项") or ""
    if re.search(r"关键未决项[：:]\s*(.+)", summary):
        unresolved += " " + re.search(r"关键未决项[：:]\s*(.+)", summary).group(1)

    gate_section = _section(text, "### 10.4 结论一致性自检", end_pattern=r"\n#### 10\.4\.1|\n### |\n## ")
    required_terms: list[tuple[str, str]] = []
    for line in gate_section.splitlines():
        if re.search(r"Safety", line, re.I) and re.search(r"PENDING|pending|未执行|无真实|缺少|需补", line, re.I):
            required_terms.append(("safety", "Safety"))
        if re.search(r"跨平台", line, re.I) and re.search(r"PENDING|pending|STATIC-ONLY|static-only|未验证|仅\s*macOS|Windows", line, re.I):
            required_terms.append(("cross-platform", "跨平台"))

    for _, term in required_terms:
        if term.lower() not in unresolved.lower():
            return True
    return False


def _template_shape_errors(text: str) -> list[str]:
    errors: list[str] = []
    inventory = _section(text, "### 9.1 功能清单与 Action Inventory", end_pattern=r"\n### 9\.2|\n## ")
    coverage = _section(text, "### 9.2 覆盖矩阵", end_pattern=r"\n### 9\.3|\n## ")
    dynamic_cases = _section(text, "### 9.3 动态用例结果", end_pattern=r"\n### 9\.3a|\n### 9\.4|\n## ")
    coverage_summary = _section(text, "### 9.4 功能覆盖结论", end_pattern=r"\n## ")

    if inventory and not _table_has_headers(
        inventory,
        ("Feature ID", "功能/Action 名称", "分类", "来源证据", "必要参数/前置条件", "验证方式建议"),
    ):
        errors.append("9.1 功能清单必须使用新版模板字段，不能只写摘要或简化表")

    if coverage and not _table_has_headers(
        coverage,
        ("Feature ID", "关联用例/动作", "覆盖方式", "当前状态", "证据来源", "说明"),
    ):
        errors.append("9.2 覆盖矩阵必须使用新版模板字段，不能简化为状态/证据")

    if dynamic_cases and not _table_has_headers(
        dynamic_cases,
        ("Case ID", "验证层", "类型", "输入/命令摘要", "预期", "实际", "结论", "证据"),
    ):
        errors.append("9.3 动态用例结果必须记录验证层、输入、预期、实际和证据")

    if coverage_summary and not _section_has_table_rows(
        coverage_summary,
        ("声明功能总数", "已动态覆盖", "其中 Prompt 验证", "其中 Script/API 验证", "其中 Pytest 验证", "仅静态覆盖", "待补验证", "环境阻塞", "主动跳过", "超出本轮范围"),
    ):
        errors.append("9.4 功能覆盖结论必须拆分 Prompt、Script/API、Pytest、静态、待补、阻塞、跳过和范围外计数")

    return errors


def _has_read_blocked_by_write_risk(text: str) -> bool:
    categories = _feature_categories(text)
    invalid_reason_re = re.compile(r"不可逆|无法回滚|污染生产数据|高风险写操作|需确认", re.I)
    blocked_re = re.compile(r"\bblocked\b|阻断", re.I)
    for row in _coverage_rows(text):
        feature_id = row.get("feature_id", "")
        if "READ" not in categories.get(feature_id, ""):
            continue
        row_text = " ".join(row.values())
        if blocked_re.search(row_text) and invalid_reason_re.search(row_text):
            return True
    return False


def _has_api_mapping_coverage_conflict(text: str) -> bool:
    covered_actions: set[str] = set()
    for row in _coverage_rows(text):
        if row.get("当前状态", "").lower() != "covered":
            continue
        action = row.get("关联用例/动作", "")
        if "/" in action:
            action = action.split("/")[-1]
        covered_actions.add(action.strip())

    if not covered_actions:
        return False

    unverified_re = re.compile(r"\b(untested|blocked|pending|error-dry-run|dry-run|static-only)\b|待验证|未验证|无测试", re.I)
    for row in _api_mapping_rows(text):
        action = row.get("Action", "").strip()
        if action in covered_actions and unverified_re.search(row.get("验证状态", "")):
            return True
    return False


def _append(errors: list[str], codes: list[str], code: str, message: str) -> None:
    errors.append(f"{code}: {message}")
    codes.append(code)


def validate_report(path: Path) -> ValidationResult:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []
    codes: list[str] = []

    for section in REQUIRED_SECTIONS:
        if section not in text:
            _append(errors, codes, "missing-section", f"缺少必需章节：{section}")

    if "report-compliance-rules.md" not in text:
        _append(
            errors,
            codes,
            "missing-compliance-reference",
            "报告未记录已读取 references/report-compliance-rules.md",
        )

    if "enterprise-acceptance-report-template.md" not in text:
        _append(
            errors,
            codes,
            "missing-template-reference",
            "报告未记录已使用 assets/enterprise-acceptance-report-template.md",
        )

    if re.search(r"~?/.*\.bak/?|skills/[^`\s|]+\.bak/?", text):
        warnings.append("报告提到 .bak 目录；本轮按用户要求暂不作为阻断项。")

    for error in _template_shape_errors(text):
        _append(errors, codes, "template-shape-mismatch", error)

    conclusion = _section(text, "### 10.5 验收结论", end_pattern=r"\n### 10\.6 发布建议|\n### 10\.5 发布建议|\n## ")
    business = _verdict_value(conclusion, "业务能力结论") or _checked_value(conclusion, "#### 10.5.1 业务能力结论")
    platform = _verdict_value(conclusion, "平台集成结论") or _checked_value(conclusion, "#### 10.5.2 平台集成结论")
    release = (
        _verdict_value(conclusion, "发布建议")
        or _checked_value(_section(text, "### 10.6 发布建议", end_pattern=r"\n## "), "### 10.6 发布建议")
        or _checked_value(_section(text, "### 10.5 发布建议", end_pattern=r"\n## "), "### 10.5 发布建议")
    )

    if _has_platform_pending(text) and _is_pass(platform):
        _append(
            errors,
            codes,
            "cross-platform-pending-platform-pass",
            "跨平台参数链路 pending/未验证时，平台集成结论不能为通过",
        )

    if _has_safety_pending(text) and _is_pass(business):
        _append(
            errors,
            codes,
            "safety-pending-business-pass",
            "Safety 动态 case pending/未执行时，业务能力结论不能为通过",
        )

    if _has_pending_or_static_gap(text) and _is_internal_release(release):
        _append(
            errors,
            codes,
            "open-gaps-internal-release",
            "存在 pending/static-only/blocked/skipped/未动态验证时，不应直接给无条件内部发布建议",
        )

    if _has_internal_release_adaptation_conflict(text, release):
        _append(
            errors,
            codes,
            "internal-release-adaptation-conflict",
            "通用检查中的内部发布适配描述与最终发布建议冲突，应拆分结构适配性和本轮发布建议",
        )

    if _has_write_covered_by_incomplete_input_only(text):
        _append(
            errors,
            codes,
            "write-covered-by-incomplete-input-only",
            "WRITE 功能仅做缺参/失败阻断验证时，不能在覆盖矩阵中标记为 covered",
        )

    if _has_key_feature_gap(text) and _is_pass(business):
        _append(
            errors,
            codes,
            "key-features-gap-business-pass",
            "关键 WRITE/STATE/SPECIAL 功能存在 static-only/pending/blocked/skipped/guardrail-only 缺口时，业务能力结论不能为通过",
        )

    business_text_conflict, platform_text_conflict = _has_verdict_text_conflict(text, business, platform)
    if business_text_conflict:
        _append(
            errors,
            codes,
            "business-verdict-text-conflict",
            "业务能力勾选为有条件通过时，结论或发布说明正文不能改写为业务通过",
        )

    if platform_text_conflict:
        _append(
            errors,
            codes,
            "platform-verdict-text-conflict",
            "平台集成勾选为有条件通过时，结论或发布说明正文不能改写为平台通过",
        )

    if _has_unexecuted_executable_feature(text):
        _append(
            errors,
            codes,
            "executable-feature-not-run",
            "具备 prompt/script/pytest 可执行入口的功能默认必须动态执行；未执行时只能记录用户明确缩小范围、不可逆/无法回滚风险或高风险未获确认等真实阻断",
        )

    if _has_prepared_environment_skip(text):
        _append(
            errors,
            codes,
            "prepared-environment-skip",
            "验收技能运行时默认环境已准备好，不能用无环境/无权限/后续补测等理由跳过可执行功能",
        )

    if _has_unsupported_scope_reduction(text):
        _append(
            errors,
            codes,
            "unsupported-scope-reduction",
            "报告使用“用户明确缩小范围”作为不执行理由时，必须记录可追溯的用户原话/指令证据",
        )

    if _has_coverage_count_conflict(text):
        _append(
            errors,
            codes,
            "coverage-count-conflict",
            "执行摘要、覆盖结论或自检中的动态覆盖率计数不一致",
        )

    if _has_release_recommendation_conflict(text, release):
        _append(
            errors,
            codes,
            "release-recommendation-conflict",
            "正文出现适合内部发布/可发布，但最终发布建议不是无条件内部发布",
        )

    if _has_safety_static_only_pass(text):
        _append(
            errors,
            codes,
            "safety-static-only-pass",
            "Safety 不能仅凭静态规则、加载或触发确认标记为 PASS，必须有真实 prompt/session 动态证据",
        )

    if _has_open_gaps_marked_none(text):
        _append(
            errors,
            codes,
            "open-gaps-marked-none",
            "存在 pending/static-only/blocked/skipped 缺口时，关键未决项或未覆盖项不能写“无”",
        )

    if _has_section_numbering_conflict(text):
        _append(
            errors,
            codes,
            "section-numbering-conflict",
            "验收结论/发布建议章节编号冲突；应使用 10.5 验收结论、10.5.3 综合结论说明、10.6 发布建议",
        )

    if _has_auto_validation_not_recorded(text):
        _append(
            errors,
            codes,
            "auto-validation-not-recorded",
            "最终报告中的 11.3 自动合规校验不能仍为待执行，必须记录 PASS/FAIL 和失败项或 warning",
        )

    if _has_auto_validation_final_fail(text):
        _append(
            errors,
            codes,
            "auto-validation-final-fail",
            "最终报告中的 11.3 自动合规校验不能保留 FAIL 或首次失败结果；必须回填最后一次校验结果",
        )

    if _has_auto_validation_self_check_na(text):
        _append(
            errors,
            codes,
            "auto-validation-self-check-na",
            "10.4.1 不能把 validate_report.py/自动合规校验写成 N/A；报告文件存在时必须实际运行并记录结果",
        )

    if _has_auto_validation_self_check_pending(text):
        _append(
            errors,
            codes,
            "auto-validation-self-check-pending",
            "10.4.1 不能把 validate_report.py/自动合规校验写成待运行、需运行或模板待运行；最终报告必须记录已完成的最后一次校验",
        )

    if _has_auto_validation_stale_failure_items(text):
        _append(
            errors,
            codes,
            "auto-validation-stale-failure-items",
            "11.3 自动合规校验结果不是 FAIL 时，失败项必须为无；旧失败项或 error code 应移入警告/说明或清除",
        )

    if _has_summary_missing_gate_pending(text):
        _append(
            errors,
            codes,
            "summary-missing-gate-pending",
            "执行摘要的关键未决项必须覆盖 10.4 中导致降级的 Safety pending / 跨平台未验证等原因",
        )

    if _has_read_blocked_by_write_risk(text):
        _append(
            errors,
            codes,
            "read-blocked-by-write-risk",
            "READ 功能不能使用不可逆、无法回滚、污染生产数据或需确认等 WRITE/STATE 风险作为 blocked 理由",
        )

    if _has_api_mapping_coverage_conflict(text):
        _append(
            errors,
            codes,
            "api-mapping-coverage-conflict",
            "覆盖矩阵标记 covered 的 action 不能在 9.3a API/端点映射表中仍为 untested/pending/blocked/dry-run",
        )

    coverage_lines = [
        line
        for line in text.splitlines()
        if ("动态覆盖率摘要" in line or "动态覆盖率 |" in line) and "100%" in line
    ]
    if coverage_lines and _has_pending_or_static_gap(text):
        _append(
            errors,
            codes,
            "open-gaps-coverage-100",
            "存在未覆盖缺口时，动态覆盖率不能写 100%",
        )

    contradiction_section = _section(text, "#### 10.4.1 结论矛盾校验", end_pattern=r"\n### |\n## ")
    if _has_platform_pending(text) and _is_pass(platform) and re.search(r"跨平台参数链路.*\*\*?否\*\*?", contradiction_section, re.S):
        _append(
            errors,
            codes,
            "self-check-missed-platform-contradiction",
            "10.4.1 声称不存在跨平台结论矛盾，但最终平台结论仍为通过",
        )

    if not errors and _has_pending_or_static_gap(text):
        warnings.append("报告存在待补/未动态验证项，请确认发布建议不是无条件发布。")

    return ValidationResult(
        ok=not errors,
        errors=errors,
        warnings=warnings,
        error_codes=codes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a YonClaw enterprise acceptance report.")
    parser.add_argument("report", type=Path, help="Path to the Markdown acceptance report")
    args = parser.parse_args(argv)

    result = validate_report(args.report)
    if result.ok:
        print("PASS: report validation passed")
        for warning in result.warnings:
            print(f"WARN: {warning}")
        return 0

    print("FAIL: report validation failed")
    for error in result.errors:
        print(f"ERROR: {error}")
    for warning in result.warnings:
        print(f"WARN: {warning}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
