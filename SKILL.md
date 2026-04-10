---
name: yonclaw-skill-acceptance
description: Use when a new or updated YonBIP skill running in YonClaw needs release validation before YonClaw rollout or marketplace-style publishing.
metadata: {"yonbip":{"version":"1.0.0"}}
---

# YonClaw Skill Acceptance

Use this skill as a release gate for a YonBIP skill running in YonClaw. It combines BIP specification checks, general-convention checks, feature-inventory analysis, dynamic behavior checks, and strict evidence recording so the final decision is based on real results instead of assumption.

After validation, the default deliverable is a Markdown enterprise acceptance report, not just a chat summary.

## When To Use

- A new YonBIP skill has been created and needs release validation.
- An existing skill was edited and must be regression-checked.
- The user wants to know whether the skill follows authoring conventions or spec expectations.
- The user wants to know whether the skill follows general release conventions and is suitable for ClawHub-style publishing.
- The user wants evidence from the runtime platform, real prompts, and a BIP-style acceptance report.
- The user wants the results backfilled into an acceptance document.

Do not use this skill for generic prompt testing unrelated to YonBIP or YonClaw skills.

This skill is for validation and reporting only. It must not proactively modify the target skill, patch business scripts, or "fix as it goes" unless the user explicitly asks for a separate repair task after validation.

## Core Rules

1. Separate spec checks, static checks, general-convention checks, feature-inventory checks, and dynamic checks.
2. Treat runtime-platform discoverability as necessary but not sufficient.
3. Always run at least one positive case, one non-trigger case, and one safety case when applicable.
4. Never claim a case passed unless there is actual command output or a real session result.
5. Keep unexecuted cases marked as pending or blocked; do not upgrade them to covered in the final summary.
6. Record environment noise separately from skill behavior.
7. Record spec violations even if the skill still loads.
8. Unless the user explicitly asks for summary-only output, generate a Markdown report file at the end.
9. Treat release readiness as a distinct outcome from simple "it loads".
10. Extract the target skill's declared feature checklist before dynamic testing.
11. Use the feature checklist to drive case coverage and report coverage gaps explicitly.
12. Do not change the target skill, shared dependency skill, or business scripts during acceptance unless the user explicitly switches from validation to repair.
13. `static-only` evidence must remain distinct from real dynamic coverage in both the matrix and the conclusion.
14. Final output must separate business capability readiness from platform or integration readiness.
15. Sensitive capabilities must be audited explicitly rather than buried inside generic static findings.
16. Choose the validation mode explicitly: single-skill deep acceptance or batch triage, and do not mix their conclusions.
17. Automatically executed behavior such as hooks, dynamic injection, or load-time commands must be surfaced as first-class risk signals.
18. Hidden or obfuscated content must be checked explicitly rather than assumed absent.
19. BIP metadata is mandatory: `name` must match the directory name, and `metadata` must include a `yonbip.version` field in `major.minor.patch` format.
20. BIP naming rules must be checked explicitly: lowercase letters or digits with hyphens only, no leading or trailing hyphen, no double hyphen, no underscore, no leading digit, and reasonable alignment with the product-line or service naming convention.
21. The body must be judged as an SOP, not a casual explanation. It should clearly cover purpose, execution steps, input and output examples, and error handling.
22. If scripts exist, treat Python-only implementation, standardized JSON output, and exception normalization as required BIP checks rather than optional general conventions.
23. For BIP API skills, verify whether scripts use the standard shared utilities such as `yonbip_skill_utils.requests` and `yonbip_skill_utils.logging` unless a justified alternative is documented.

## Acceptance Workflow

### 0. Choose the validation mode

Decide which mode applies before reading too much:

- `single-skill deep acceptance`: use for release-gating one target skill with full spec, runtime, and report output
- `batch triage`: use for scanning multiple skills quickly, ranking risk, and deciding which ones deserve deep acceptance next

Rules:

- batch triage may reuse the sensitive-capability and hidden-content checks, but it must not pretend to provide the same depth as full acceptance
- deep acceptance remains the required mode for any final release verdict such as `通过`, `有条件通过`, or `不通过`
- batch triage should end with a shortlist: `needs deep acceptance`, `safe for now`, or `high-risk`

### 1. Confirm the test target

Capture:

- skill name
- skill path
- intended workspace
- target acceptance document path if one already exists
- whether the target is internal release only or marketplace publishing

If the skill lives outside the active YonClaw workspace, create or use an isolated validation workspace rather than editing the user's normal environment more than needed.

### 2. Run static checks

Verify:

- `SKILL.md` exists
- frontmatter contains `name` and `description`
- referenced scripts or references actually exist
- the skill instructions match the intended behavior

### 2a. Run spec checks

Check whether the skill follows common authoring expectations:

- `description` is trigger-oriented and preferably starts with `Use when`
- `description` focuses on when to use the skill, not a long summary of workflow
- `description` explicitly states what the skill does, how a user would ask for it, and the likely trigger keywords
- `name` matches the directory name exactly
- `metadata` exists and is valid YAML frontmatter content
- `metadata.yonbip.version` exists and uses `major.minor.patch`
- if runtime-platform metadata exists, it is not stale or contradictory
- `name` is stable, readable, and hyphenated if appropriate
- `agents/openai.yaml` exists when UI metadata is expected
- `agents/openai.yaml` matches the skill intent and is not stale
- if the skill is part of a dedicated skill git project, the git project name follows the BIP `microservice-code-skills` convention or a documented equivalent
- if the skill is part of a dedicated skill git project, the surrounding project structure is consistent with the BIP expectation that one project may contain one or more skill directories following the standard layout
- the skill directory does not contain unnecessary auxiliary docs that should not be part of the skill itself
- references, scripts, and assets are placed in sensible subdirectories
- the directory name follows BIP naming constraints: lowercase, hyphenated, no underscore, no double hyphen, no leading digit

Mark each spec issue separately from runtime issues. A spec issue may justify `有条件通过` even when dynamic cases succeed.

### 2b. Run general-convention release audit

Check whether the skill is publication-ready, not merely functional:

- trigger precision: `description` is concise, trigger-oriented, and does not summarize the whole workflow
- progressive disclosure: the skill tells the model to load only the files or resources actually needed
- resource organization: `scripts/`, `references/`, `assets/`, and `agents/` have clear roles
- evidence discipline: the skill requires real command output or session evidence before passing cases
- failure visibility: pending, failed, and environment-noise items remain visible in the report
- report completeness: the default deliverable is a structured report, not only a chat summary
- marketplace readiness: naming, metadata, directory cleanliness, and output behavior are suitable for publishing
- untrusted-input defense: external web or document content is treated as data, not as executable instruction

Mark general-convention gaps separately from spec failures and runtime failures.

### 2c. Run sensitive-capability audit

Identify whether the skill or its referenced scripts possess sensitive powers beyond normal prompt-only behavior. At minimum, inspect for:

- system command execution such as `subprocess`, `os.system`, shell wrappers, or script launchers
- local sensitive file access such as browser cookies, SQLite databases, auth caches, key files, or workspace files outside the declared scope
- broad network reach such as arbitrary URL or path-based HTTP requests, generic API clients, proxy behavior, or upload/download helpers
- destructive or state-changing operations such as delete/cancel/end/overwrite/bulk update
- privilege mismatch where the declared feature set is narrower than the reachable implementation surface
- frontmatter risk factors such as high-power `allowed-tools`, hidden invocation, lifecycle hooks, or fork/subprocess execution modes
- load-time or trigger-time command injection such as dynamic command blocks, auto-executed shell snippets, or install-time execution
- hidden or obfuscated content such as HTML comments with instructions, base64 payloads, zero-width characters, Unicode smuggling, or embedded safety overrides

For each sensitive capability, record:

- capability type
- where it was found
- why it exists
- whether that power is clearly disclosed by the skill description or instructions
- whether the power appears proportionate to the declared use
- whether release should remain allowed, conditional, or blocked

Do not call a skill "safe" merely because no malicious code was found. If the skill has meaningful power, surface that power explicitly.

### 2d. Run auto-execution and hidden-content checks

Inspect whether the skill can execute or influence behavior before the user consciously invokes it.

At minimum, check:

- lifecycle hooks or platform-specific auto-run fields
- dynamic injection patterns that execute shell or tool commands during skill load
- hidden trigger patterns intended to evade ordinary review
- comments, encoded payloads, or invisible characters that alter instructions or override safety policy
- browser-cookie, local-database, or auth-cache access that is not clearly disclosed

Record separately:

- whether the behavior is auto-executed, user-triggered, or unclear
- whether the behavior is documented
- whether the behavior is necessary for the stated use
- whether the behavior should block release

### 3. Run platform integration checks

Use the runtime platform commands appropriate to the validation environment.

```bash
<runtime-platform-refresh-command>
<runtime-platform-list-command>
<runtime-platform-info-command> <skill-name>
```

Pass criteria:

- the runtime platform reloads or refreshes successfully
- the skill becomes discoverable in the runtime
- the runtime info or metadata command resolves to the expected directory and file set

If YonClaw is not using the intended workspace, document that fact and, if appropriate, temporarily switch to an isolated validation workspace. Record the exact workspace used.

### 3a. Extract the feature inventory

Before dynamic testing, read the target skill and build a feature inventory from:

- explicit feature lists in `SKILL.md`
- capability bullets such as “支持…”
- operation verbs such as query/create/update/delete/export/review/reply
- branch-specific guardrails, placeholders, confirmation requirements, and output-format rules
- referenced scripts that imply concrete subcommands or operation families

For each feature, record:

- feature id
- feature name
- source evidence in the skill file or referenced resource
- feature category:
  - core operation
  - guardrail
  - branch behavior
  - output rule
  - integration requirement
  - BIP compliance requirement
- whether dynamic validation is required, optional, or blocked by environment

Do not treat one happy path as proof that all listed features work.

### 3b. Build the coverage matrix

Create a feature-to-case matrix before running dynamic checks.

At minimum, classify planned coverage as:

- covered by dynamic case
- covered by static/spec evidence only
- pending due to environment or prerequisite gap
- blocked by environment or platform failure
- out of scope for this round

Prefer one case to cover multiple nearby features only when the evidence remains explicit and unambiguous.

### 4. Run dynamic behavior checks

At minimum, test these baseline prompt classes:

- Positive: should trigger the skill
- Negative: should not trigger the skill
- Incomplete input: should guide, not invent
- Safety: should refuse or guard risky actions

When the skill has operation-specific behavior, add focused cases for those branches.

Dynamic checks must include:

- baseline cases:
  - Positive
  - Negative
  - Incomplete input
  - Safety
- feature-specific cases derived from the feature inventory

For multi-operation skills, aim to cover each important operation family at least once. For example:

- query/list/search
- create/send/submit
- update/edit/reply
- delete/cancel/end
- export/report/render
- review/approval/audit

If some operations cannot be safely run in the current environment, keep them visible in the matrix as pending and explain the blocker.

### 4a. Run BIP script compliance checks

When the target skill includes `scripts/`, inspect whether the implementation follows BIP script conventions:

- scripts are implemented in Python rather than mixed arbitrary runtimes unless clearly justified
- script names follow lowercase underscore style
- BIP API access uses `yonbip_skill_utils.requests` or a documented equivalent wrapper
- logging uses `yonbip_skill_utils.logging` or a documented equivalent
- final script output is printed as JSON and includes at least `success` and `message`
- exceptions are normalized into standard output rather than thrown raw

Record these results separately from dynamic business behavior so a skill can be functionally useful yet still fail BIP engineering compliance.

For each case, record:

- prompt
- expected behavior
- actual behavior
- pass or pending
- run identifier or equivalent evidence when available
- covered feature ids

### 5. Evaluate behavior, not just trigger

Check whether the model actually followed the skill's rules. For example:

- placeholders were used instead of live secrets
- summaries were trimmed as specified
- dangerous actions were not executed by default
- missing inputs were called out instead of fabricated
- declared feature branches were actually exercised rather than assumed
- operation-specific outputs matched the documented contract

### 5a. Evaluate coverage completeness

After dynamic testing, evaluate the feature inventory itself:

- Which declared features were dynamically covered?
- Which features only have static evidence?
- Which features remain pending?
- Which features were blocked by environment or platform conditions?
- Which critical features are still unverified?

Do not mark `通过` when critical declared features remain untested unless the user explicitly narrowed scope and that narrower scope is recorded.

### 5b. Optional second-opinion review

When risk classification remains ambiguous, or when the skill has meaningful sensitive power, optionally request a second-model or second-tool review.

Use this branch when:

- the primary audit is near a pass/fail boundary
- static evidence suggests risky power but intent is unclear
- the user explicitly wants cross-validation

Rules:

- treat the second opinion as advisory evidence, not automatic truth
- preserve the original findings and note where the second opinion agreed or disagreed
- never let a second opinion erase direct evidence from code or runtime behavior

### 6. Backfill the acceptance record

Update the acceptance document with:

- executive summary
- risk summary card
- spec findings
- general-convention audit findings
- sensitive-capability audit findings
- auto-execution and hidden-content findings
- feature inventory
- coverage matrix
- commands executed
- real results
- pending cases
- known environment issues
- current conclusion
- release recommendation

If no acceptance document exists yet, create one from the bundled enterprise template at `assets/enterprise-acceptance-report-template.md`.

Preferred output behavior:

- If the user already has an acceptance doc path, update that file.
- Otherwise, create a new Markdown report in the current workspace.
- Use a file name like `<skill-name>-acceptance-report-enterprise.md`.
- Fill executed items with evidence, keep unexecuted items as pending or blocked, and do not hide failures.
- Do not "repair while validating"; record findings and stop at report output unless the user explicitly asks for fixes.
- Do not mark a feature as `covered` unless dynamic evidence exists in the report.
- Split the final verdict into:
  - business capability conclusion
  - platform / integration conclusion
- If sensitive powers exceed the declared use or lack clear disclosure, prefer `有条件通过` or `不通过` over `通过`.

Preferred conclusion states:

- `通过`: all critical checks and planned cases passed
- `有条件通过`: key checks passed but remaining cases or environment issues still exist
- `不通过`: loading failed, behavior is wrong, or safety behavior is unacceptable

Preferred release recommendation states:

- `适合 YonClaw 发布`
- `适合发布到 ClawHub`
- `修复后再发布`

### Batch-triage output minimum

When running batch triage instead of deep acceptance, the output must still include:

- skill name
- claimed purpose
- source / location
- highest observed risk level
- whether deep acceptance is required next
- concise reason grounded in evidence

## Minimum Case Set

Use this default set unless the skill needs more:

1. Positive case
2. Negative case
3. Incomplete-input case
4. Safety case

For broader acceptance, expand to:

1. Happy path
2. Secondary happy path
3. Boundary case
4. Negative case
5. Error-input case
6. Safety case

For feature-rich skills, expand again into:

1. Baseline case set
2. One case per important operation family
3. One case per critical guardrail
4. One case per special output-format rule
5. One case per destructive or high-risk action path

## Evidence Standard

Good evidence includes:

- direct references to the skill file and relevant lines
- runtime platform discovery output showing the skill
- runtime info output showing the resolved path
- actual runtime agent results
- gateway or runtime warnings captured as environment notes
- direct mapping from executed cases to declared features
- direct evidence of `metadata.yonbip.version`, SOP structure, script output shape, and exception handling behavior when applicable

Do not treat assumptions, static reading, or inferred behavior as dynamic proof.

## Report Requirement

The final output should normally include both:

1. A concise chat summary
2. A Markdown report file generated from the enterprise template

The report must contain:

- document info
- skill name and path
- workspace used for validation
- spec findings
- BIP compliance findings
- static check results
- general-convention audit results
- dynamic case results
- environment issues
- final conclusion
- release recommendation
- next actions

When possible, include file references, command evidence, and run identifiers.

## Common Mistakes

- Marking a case passed because the prompt "looks like it should trigger"
- Treating "loads successfully" as proof that the skill is spec-compliant
- Treating generic runtime compatibility as proof that BIP metadata and SOP rules are compliant
- Treating "spec-compliant" as proof that the skill is release-ready
- Treating one successful operation as proof that every listed feature works
- Skipping feature inventory extraction for multi-operation skills
- Quietly editing the target skill during acceptance without explicit user approval
- Ignoring gateway warnings that may affect stability
- Mixing skill defects with environment defects
- Forgetting to note when YonClaw was temporarily pointed at a validation workspace
- Converting pending checks into passed checks during document cleanup
- Ignoring script output shape, logging, or exception normalization when the skill contains Python scripts

## Closeout

Before closing:

- confirm which cases truly ran
- separate spec violations from behavior failures
- separate general-convention gaps from runtime failures
- summarize declared feature coverage, not only case counts
- keep unresolved cases visible
- summarize environment caveats separately
- ensure the report file was written or clearly state why it was not
- state whether the skill is ready for internal use, ClawHub publishing, further testing, or repair
