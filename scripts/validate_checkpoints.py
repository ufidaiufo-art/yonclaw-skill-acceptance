#!/usr/bin/env python3
"""Validate staged checkpoint artifacts before report generation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_STATUSES = {"covered", "failed", "blocked", "skipped", "not_applicable"}
TERMINAL_WITH_REASON = {"failed", "blocked", "skipped", "not_applicable"}
REQUIRED_SKILL_INFO_KEYS = {"skill", "read_files", "features"}
REQUIRED_TEST_CASE_TYPES = {"positive", "negative", "incomplete_input", "safety"}


def _load_json(path: Path, errors: list[str]) -> Any:
    if not path.exists():
        errors.append(f"missing file: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path}: {exc}")
        return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _template_ids(template: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id"))
        for item in _as_list(template.get("checkpoints"))
        if item.get("id")
    }


def _feature_ids(skill_info: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for feature in _as_list(skill_info.get("features")):
        if isinstance(feature, dict) and feature.get("id"):
            ids.add(str(feature["id"]))
    return ids


def _validate_skill_info(skill_info: Any, errors: list[str]) -> set[str]:
    if not isinstance(skill_info, dict):
        errors.append("skill-info.json must be an object")
        return set()
    missing = REQUIRED_SKILL_INFO_KEYS - set(skill_info)
    if missing:
        errors.append(f"skill-info.json missing keys: {', '.join(sorted(missing))}")
    skill = skill_info.get("skill")
    if not isinstance(skill, dict) or not skill.get("name") or not skill.get("path"):
        errors.append("skill-info.json skill must include name and path")
    read_files = _as_list(skill_info.get("read_files"))
    if not read_files:
        errors.append("skill-info.json read_files must not be empty")
    elif not any(str(item).endswith("SKILL.md") for item in read_files):
        errors.append("skill-info.json read_files must include target SKILL.md")
    features = _as_list(skill_info.get("features"))
    if not features:
        errors.append("skill-info.json features must not be empty")
    return _feature_ids(skill_info)


def _validate_tests(test_results: Any, errors: list[str]) -> None:
    if not isinstance(test_results, dict):
        errors.append("test-results.json must be an object")
        return
    tests = _as_list(test_results.get("tests") or test_results.get("test_results"))
    if not tests:
        errors.append("test-results.json tests must not be empty")
        return
    seen_types: set[str] = set()
    for index, test in enumerate(tests, start=1):
        if not isinstance(test, dict):
            errors.append(f"test-results.json test #{index} must be an object")
            continue
        case_type = str(test.get("type") or "").strip()
        if case_type:
            seen_types.add(case_type)
        if not test.get("id"):
            errors.append(f"test-results.json test #{index} missing id")
        if not test.get("evidence"):
            errors.append(f"test-results.json test #{index} missing evidence")
        if not test.get("result"):
            errors.append(f"test-results.json test #{index} missing result")
    missing_types = REQUIRED_TEST_CASE_TYPES - seen_types
    if missing_types:
        errors.append(f"test-results.json missing baseline case types: {', '.join(sorted(missing_types))}")


def _validate_checkpoints(
    checkpoints_doc: Any,
    required_ids: set[str],
    feature_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not isinstance(checkpoints_doc, dict):
        errors.append("checkpoints-covered.json must be an object")
        return
    checkpoints = _as_list(checkpoints_doc.get("checkpoints"))
    if not checkpoints:
        errors.append("checkpoints-covered.json checkpoints must not be empty")
        return
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(checkpoints, start=1):
        if not isinstance(item, dict):
            errors.append(f"checkpoint #{index} must be an object")
            continue
        checkpoint_id = str(item.get("id") or "").strip()
        if not checkpoint_id:
            errors.append(f"checkpoint #{index} missing id")
            continue
        by_id[checkpoint_id] = item
        status = str(item.get("status") or "").strip()
        if status not in ALLOWED_STATUSES:
            errors.append(f"{checkpoint_id}: invalid status {status!r}")
        evidence = item.get("evidence")
        reason = item.get("reason")
        coverage = item.get("coverage")
        if status == "covered" and not evidence:
            errors.append(f"{checkpoint_id}: covered checkpoint must include evidence")
        if status in TERMINAL_WITH_REASON and not reason:
            errors.append(f"{checkpoint_id}: {status} checkpoint must include reason")
        if not coverage:
            warnings.append(f"{checkpoint_id}: coverage location is empty")

    missing_required = sorted(required_ids - set(by_id))
    if missing_required:
        errors.append(f"missing fixed checkpoint IDs: {', '.join(missing_required)}")

    # Feature IDs are allowed to be represented by derived checkpoint IDs such
    # as FEATURE-F001 or DYNAMIC-F001. Require at least one checkpoint to mention
    # each feature id in id, feature_id, or source_feature_id.
    for feature_id in sorted(feature_ids):
        found = False
        for item in by_id.values():
            values = {
                str(item.get("id") or ""),
                str(item.get("feature_id") or ""),
                str(item.get("source_feature_id") or ""),
            }
            if feature_id in values or any(value.endswith(f"-{feature_id}") for value in values):
                found = True
                break
        if not found:
            errors.append(f"missing target feature checkpoint for feature: {feature_id}")


def validate(template_path: Path, skill_info_path: Path, checkpoints_path: Path, test_results_path: Path) -> tuple[bool, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    template = _load_json(template_path, errors)
    skill_info = _load_json(skill_info_path, errors)
    checkpoints = _load_json(checkpoints_path, errors)
    test_results = _load_json(test_results_path, errors)
    if errors:
        return False, errors, warnings

    required_ids = _template_ids(template)
    if not required_ids:
        errors.append("checkpoint template contains no checkpoints")
    feature_ids = _validate_skill_info(skill_info, errors)
    _validate_tests(test_results, errors)
    _validate_checkpoints(checkpoints, required_ids, feature_ids, errors, warnings)
    return not errors, errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate YonClaw staged checkpoint artifacts.")
    parser.add_argument("--template", type=Path, default=Path(__file__).resolve().parents[1] / "assets" / "checkpoints.json")
    parser.add_argument("--skill-info", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--test-results", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ok, errors, warnings = validate(args.template, args.skill_info, args.checkpoints, args.test_results)
    if args.json:
        print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings}, ensure_ascii=False, indent=2))
    else:
        print("PASS" if ok else "FAIL")
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARN: {warning}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
