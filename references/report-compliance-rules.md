# Report Compliance Rules

This file is mandatory for every `single-skill deep acceptance` report.

Before writing any final verdict or release recommendation, read and apply these rules. If this file was not read in the current run, the report is invalid and must not mark `pass` or `internal release`.

## Required Structure

An enterprise acceptance report must use `assets/enterprise-acceptance-report-template.md` and include these sections:

- `8.3 异常输入与副作用审计`
- `9.1 功能清单与 Action Inventory`
- `9.2 覆盖矩阵`
- `9.3 动态用例结果`
- `9.4 功能覆盖结论`
- `10.4 结论一致性自检`
- `10.4.1 结论矛盾校验`
- `10.5 验收结论`
- `10.6 发布建议`

If `10.4` or `10.4.1` is missing, the report is invalid and must not output `通过` or `适合 YonClaw 内部发布`.

Template use means preserving the required table schemas, not only copying section titles. The report is invalid if it simplifies these tables:

- `9.1` must include `Feature ID / 功能/Action 名称 / 分类 / 来源证据 / 必要参数/前置条件 / 验证方式建议 / 备注`.
- `9.2` must include `Feature ID / 关联用例/动作 / 覆盖方式 / 当前状态 / 证据来源 / 说明`.
- `9.3` must include `Case ID / 验证层 / 类型 / 输入/命令摘要 / 预期 / 实际 / 结论 / 证据`.
- `9.4` must separately count prompt, script/API, pytest, static-only, pending, blocked, skipped, and out-of-scope items.

## Evidence Rules

- `covered` requires real command output, runtime session output, API response, pytest output, or equivalent executable evidence.
- `static-only` is not dynamic coverage.
- `READ` features are read-only by definition. They must not be blocked using `不可逆`, `无法回滚`, `污染生产数据`, `需确认`, or other WRITE/STATE risk reasons.
- `WRITE / STATE` features may be blocked only with a concrete rollback, confirmation, or production-pollution reason.
- If a feature has a `prompt`, `script/api`, `pytest`, or equivalent executable entry point, it must be executed by default.
- When this acceptance skill runs, the validation environment is assumed to be prepared. Missing environment, missing permission, auth unavailable, cross-platform environment unavailable, or "test later" are not valid skip reasons.
- A non-executed executable feature is valid only when the report records a true blocking reason: user explicitly narrowed scope, user refused a high-risk action, the action is irreversible and cannot be rolled back, or execution would pollute production data without isolated test data.
- If the report uses "用户明确缩小范围" as a skip/block reason, it must record traceable evidence such as `用户明确缩小范围证据：<user quote or instruction>`. Do not infer scope reduction from silence, baseline wording, time pressure, or model convenience.
- "Script exists", "static confirmation", "baseline only", "time limit", "missing environment", "missing permission", "auth failed", or "test later" are not valid reasons to skip execution.
- For `WRITE / STATE / SPECIAL` features, incomplete-input, missing-confirm, `success=false`, or fail-closed cases cover only guardrail behavior. They do not prove the business feature is `covered`.
- A `WRITE / STATE / SPECIAL` feature is dynamically `covered` only after normal execution, business re-check, and required cleanup/reversal evidence are recorded.
- Script stdout, exit code, error text, or `success=false` alone does not prove real business re-check.
- Real business re-check requires business list, detail, search, API query, or equivalent state evidence.
- Safety requires a real prompt/session case, such as refusing validate-and-fix, direct target modification, or unsafe write execution during acceptance.
- Skill loading, trigger confirmation, or reading `SKILL.md` is not a Safety pass.
- Cross-platform parameter verification requires Windows/PowerShell/cmd or documented equivalent parameter-chain evidence.

## Verdict Gate

Apply the highest allowed verdict before filling final conclusions.

- Missing `Safety` dynamic case: business verdict max is `有条件通过`.
- Missing `Incomplete-input` dynamic case: business verdict max is `有条件通过`.
- Applicable abnormal-input and side-effect audit not executed: business verdict max is `有条件通过`; release recommendation must not be `适合 YonClaw 内部发布`.
- Any key `WRITE / STATE / SPECIAL / guardrail` feature is `static-only`, `pending`, `blocked`, `skipped`, or `guardrail-only` without an explicitly narrowed scope: business verdict must not be `通过`.
- Cross-platform parameter chain is `pending`, `blocked`, or `static-only`: platform verdict max is `有条件通过`.
- Any dirty data, placeholder value, wrong association, or unknown-user business pollution: business verdict is `不通过` unless cleaned and re-verified.

## Contradiction Gate

Check these contradictions before writing final conclusions:

- If any feature is `static-only`, `pending`, `blocked`, or `skipped`, dynamic coverage must not be `100%`.
- If an executable feature remains `pending` or `static-only` without an explicit blocking reason, the report is invalid.
- Feature counts in executive summary, coverage matrix, dynamic cases, and coverage conclusion must match.
- Dynamic coverage counts in the executive summary, section `9.4`, and section `10.4` must use the same numerator and denominator.
- If text says a feature was not dynamically verified, the coverage matrix must not mark it `covered`.
- If `9.3a API/端点映射表` marks an action as `untested`, `pending`, `blocked`, `dry-run`, or `error-dry-run`, `9.2 覆盖矩阵` must not mark the same action `covered`.
- If a `WRITE / STATE / SPECIAL` feature is only tested through missing-parameter, missing-confirm, `success=false`, or fail-closed cases, the coverage matrix must not mark the business feature `covered`.
- If key `WRITE / STATE / SPECIAL` features remain `static-only`, `pending`, `blocked`, `skipped`, or `guardrail-only`, the business verdict must not be `通过`.
- The general "release adaptation" row must describe structural readiness only. It must not say the skill is suitable for internal release when the final release recommendation is not internal release.
- If Safety evidence is only static reading, trigger confirmation, or skill loading, Safety must be `pending`, not `pass`.
- A Safety pass requires real prompt/session evidence. Static rules, skill loading, trigger confirmation, or "rules followed" are not Safety dynamic evidence.
- If the self-check says a gate lowers the highest verdict, computed verdict and final verdict must be downgraded consistently.
- If findings, pending items, or open risks exist, key unresolved items must not be `无`.
- If any feature is `static-only`, `pending`, `blocked`, `skipped`, or `guardrail-only`, the report must not write `未覆盖：无` or `关键未决项：无`.
- Key unresolved items in the executive summary must include every downgrade reason from `10.4`, including Safety pending and cross-platform verification gaps.
- Section `11.3 自动合规校验` must record the actual validator result. It must not remain `待执行`, `pending`, `N/A`, or placeholder text after final conclusions are written.
- Section `11.3 自动合规校验` must record the final validator run, not the first failed run. If the final report still says `FAIL`, the report is invalid.
- If section `11.3` does not say `FAIL`, its `失败项` must be `无`/`none` or empty. Old validator error codes must not remain in `失败项`; warnings must be recorded separately as warnings.
- Section `10.4.1` must not mark `validate_report.py` or automatic compliance validation as `N/A`; if a report file exists, the validator must be runnable and recorded.
- Section `10.4.1` must not describe validator execution as `待运行`, `需运行校验器`, `模板待运行`, `待重新校验`, or equivalent after final conclusions.
- If platform verdict max is `有条件通过`, final platform verdict must not be `通过`.
- Final verdicts may be written as checkbox subsections or table rows; both forms must obey the same contradiction gates.
- Use `10.5.3 综合结论说明` under `10.5 验收结论`; do not use `10.4.3` there.
- Final release recommendation belongs in `10.6 发布建议`; do not create another top-level `10.5 发布建议`.
- If the final platform verdict is `有条件通过`, conclusion text and release recommendation text must not restate it as `通过`. Apply the same rule to business verdict text.
- Release recommendation must match the highest allowed verdict.

If any contradiction is present and not fixed, final verdict must be `有条件通过` or `不通过`, never `通过`.

## Automated Validation

After writing or updating the report, run:

```bash
python3 scripts/validate_report.py <report-path>
```

If the validator exits non-zero, the report is invalid. Fix the report or
downgrade the verdict before giving any release recommendation.

The validator must block deterministic contradictions, including:

- Required enterprise sections are missing.
- The report does not record `report-compliance-rules.md` or the enterprise template.
- The target path points to `.bak` without explicit user intent.
- Cross-platform verification is pending but the platform verdict is `通过`.
- Safety is pending but the business verdict is `通过`.
- A general check says "suitable for internal release" while the final release recommendation is not internal release.
- A `WRITE / STATE / SPECIAL` feature is marked `covered` using only incomplete-input or fail-closed evidence.
- Key `WRITE / STATE / SPECIAL` features remain `static-only` or `guardrail-only` while the business verdict is `通过`.
- Executable features remain `pending` or `static-only` without a blocking reason.
- Executable features are skipped because of missing environment, missing permission, auth unavailable, or "test later".
- A report claims "用户明确缩小范围" without recording user quote/instruction evidence.
- Dynamic coverage counts conflict across executive summary, coverage conclusion, or self-check.
- Safety is marked pass using only static reading, skill loading, trigger confirmation, or rules-followed evidence.
- Any non-final section says `适合 YonClaw 内部发布` or equivalent while the final release recommendation is `修复后再发布` or conditional.
- Open gaps exist while unresolved items or uncovered items are written as `无`.
- Executive summary omits Safety pending or cross-platform gaps that downgrade the final verdict.
- The automatic compliance validation section still says `待执行`, `pending`, or placeholder values.
- The automatic compliance validation section still says `FAIL` after final conclusions.
- The automatic compliance validation section says non-FAIL but leaves old error codes or failure text in `失败项`.
- `10.4.1` says validator execution is `N/A`.
- `10.4.1` says validator execution is still pending, template-pending, or needs to be run.
- A `READ` feature is blocked using WRITE/STATE-only reasons such as irreversible action, no rollback, production pollution, or confirmation needed.
- API mapping says an action is untested/pending/blocked/dry-run while coverage matrix marks the same action covered.
- Conclusion or release recommendation sections are misnumbered, duplicated, or split across multiple top-level `10.5` headings.
- Conclusion or release text restates a conditional platform/business verdict as `通过`.
- Pending/static-only/blocked/skipped gaps exist but the report recommends unconditional internal release.
- `10.4.1` says there is no contradiction while final conclusions still contradict gate results.

## Final Report Validity

A report is valid only when all are true:

- It uses the enterprise template structure.
- It includes `10.4` and `10.4.1`.
- It records `report-compliance-rules.md` and `assets/enterprise-acceptance-report-template.md` as applied evidence.
- It records dynamic coverage and static-only coverage separately.
- It computes the highest allowed business and platform verdicts.
- It applies all downgrade gates to final conclusions.
- It keeps unresolved items visible.
- `scripts/validate_report.py <report-path>` exits successfully.
- The required template tables keep the full enterprise schema; section-title-only or shortened tables are not valid template use.
