# YonClaw 技能验收 / YonClaw Skill Acceptance

面向 YonBIP/YonClaw skill 的发布前验收与放行检查。  
Pre-release acceptance and release-gating checks for YonBIP/YonClaw skills.

`yonclaw-skill-acceptance` 是一个用于发布把关的 YonBIP/YonClaw skill。适用于新建或更新后的 skill 在发布到 YonClaw 或 ClawHub 之前做基于证据的验收。默认输出不是聊天摘要，而是一份严格的企业级 Markdown 验收报告。  
`yonclaw-skill-acceptance` is a YonBIP/YonClaw skill for release gating. It is designed for evidence-based acceptance before a new or updated skill is rolled out internally or published to ClawHub. Its default output is not a casual chat summary, but a strict enterprise-style Markdown acceptance report.

## 简短说明 / Short Description

适用于新建或更新后的 YonBIP/YonClaw skill 在内部发布或 ClawHub 发布前进行验收验证。  
Use this skill to validate a new or updated YonBIP/YonClaw skill before YonClaw rollout or ClawHub publication.

## 市场简介 / Marketplace Summary

这个 skill 用来判断一个 YonBIP/YonClaw skill 是否真的具备发布条件。它检查的不只是“能不能被加载”，还会把 BIP 规范项与通用发布规范分开审计：BIP 规范侧覆盖命名、`description`、metadata、SOP 正文结构与 Python 脚本规范；通用规范侧覆盖触发设计、渐进披露、资源组织、证据纪律、报告完整性与发布适配。最终结果会给出结构化的企业级验收报告，并明确标注 `通过`、`有条件通过` 或 `不通过`，同时附带发布建议。  
This skill is used to determine whether a YonBIP/YonClaw skill is actually ready for release. It checks more than simple loadability. It separates BIP compliance from general release-convention auditing: the BIP side covers naming, `description`, metadata, SOP-style body structure, and Python script compliance; the general-convention side covers trigger design, progressive disclosure, resource organization, evidence discipline, report completeness, and release readiness. The final result is a structured enterprise-style acceptance report with explicit business and integration conclusions, plus release guidance.

## 检查范围 / What It Checks

- 审核 `SKILL.md`、`agents/openai.yaml`、脚本/引用路径、触发设计、渐进披露、资源布局、证据标准、失败可见性与发布适配等通用规范
- 检查是否符合 BIP Skill 开发规范中的命名、`description`、`metadata.yonbip.version`、SOP 正文结构与目录约束
- 检查技能所在 git 项目命名与项目目录结构是否符合 BIP 规范（适用时）
- 提取功能清单并评估覆盖情况
- 通过运行平台的刷新、发现、信息命令做平台集成验证
- 使用正向、负向、不完整输入和安全用例做动态验证
- 对 `scripts/` 做 BIP 脚本合规检查，包括 Python、共享请求封装、日志、标准 JSON 输出与异常处理
- 检查 grouped skills 的依赖与冲突风险
- 审计命令执行、本地敏感文件访问、宽范围 HTTP 调用等敏感能力
- 检查 hooks、动态注入、加载即执行命令等自动执行风险
- 检查隐藏内容、混淆内容、编码载荷、零宽字符和安全策略覆盖迹象
- 检查声明能力与实际能力是否存在偏差
- 支持批量筛查模式，用于先做多 skill 风险分拣，再决定哪些进入深度验收
- 在边界结论场景下可选做二次模型复核
- 基于真实证据生成报告，并将环境问题与 skill 缺陷分开记录
- 给出 YonClaw 发布或 ClawHub 发布建议

- Audits general release conventions such as `SKILL.md`, `agents/openai.yaml`, script/reference paths, trigger design, progressive disclosure, resource organization, evidence quality, failure visibility, and marketplace readiness
- Checks BIP-specific rules for naming, `description`, metadata, `metadata.yonbip.version`, SOP structure, and directory constraints
- Checks whether the surrounding skill git project naming and project layout follow BIP conventions when applicable
- Extracts the functional surface area and evaluates coverage
- Verifies platform integration with the runtime platform's refresh, discovery, and skill-info commands
- Runs positive, negative, incomplete-input, and safety test cases
- Audits `scripts/` for BIP Python, shared request wrapper, logging, JSON output, and exception-handling compliance
- Checks grouped-skill dependency and conflict risk
- Audits sensitive capabilities such as command execution, local sensitive-file access, and broad HTTP reach
- Checks hooks, dynamic injection, and load-time execution behavior
- Checks hidden content, obfuscated payloads, zero-width characters, and safety-override traces
- Checks whether the declared capability scope matches the actual reachable power
- Supports batch triage before deep acceptance when multiple skills need screening
- Allows optional second-opinion review when the conclusion sits near a release boundary
- Produces a report grounded in real evidence while separating environment noise from skill defects
- Provides a release recommendation for YonClaw rollout or ClawHub publication

## 默认输出 / Default Output

默认输出是一份企业级 Markdown 验收报告，而不是简单的聊天回复。  
The default output is an enterprise-style Markdown acceptance report, not a simple chat reply.

报告通常包含这些部分：  
The report usually includes:

- 执行摘要
- 通用规范检查
- 平台集成检查
- BIP 规范专项检查
- 安全与风险审计
  包括敏感能力审计、权限-用途匹配检查、自动执行与隐藏内容检查
- 功能与覆盖验证
- 风险与结论
- 文档信息
- 目标 skill 与工作区信息
- 后续动作与附件

- Document information
- Executive summary
- General convention check results
- Platform integration check results
- BIP-specific compliance results
- Security and risk audit results
- Consolidated feature-and-coverage validation section
- Risk and conclusion section
- Follow-up actions and evidence section
- Target skill and workspace context
- Compliance check results

## 适用场景 / When To Use

- 新 skill 首次发布前做验收
- 已修改 skill 在重新发布前做回归检查
- 判断 skill 是否适合发布到 YonClaw
- 判断 skill 是否适合发布到 ClawHub

- Acceptance before the first release of a new skill
- Regression validation before re-releasing an updated skill
- Deciding whether a skill is ready for YonClaw rollout
- Deciding whether a skill is ready for ClawHub publication

## 不适用场景 / When Not To Use

- 与 YonClaw skill 无关的普通 prompt 试验
- 没有证据记录的一次性聊天测试
- 与 skill 包无关的自由式代码审查
- 在验收过程中自动修改目标 skill

- General prompt experiments unrelated to YonBIP/YonClaw skills
- One-off chat tests without evidence capture
- Free-form code review unrelated to a skill package
- Automatically modifying the target skill during acceptance

## 示例提示词 / Example Prompt

```text
使用 $yonclaw-skill-acceptance 对这个 YonBIP/YonClaw skill 做发布验收，执行通用规范检查、BIP 规范专项检查、正向/负向/不完整输入/安全用例测试，并生成企业级验收报告。
```

```text
Use $yonclaw-skill-acceptance to run release acceptance for this YonBIP/YonClaw skill, including general convention checks, BIP-specific compliance checks, positive/negative/incomplete-input/safety tests, and generation of an enterprise-style acceptance report.
```

## 列表页文案 / Listing Copy

### 一句话介绍 / One-Line Intro

面向 YonBIP/YonClaw skill 的发布前验收工具，提供基于证据的动态验证、BIP 规范检查与企业级报告。  
Pre-release acceptance for YonBIP/YonClaw skills with evidence-based runtime validation, BIP compliance checks, and enterprise-style reporting.

### 短介绍 / Short Intro

在发布前验证 YonBIP/YonClaw skill，覆盖通用规范检查、BIP 脚本合规、功能覆盖、动态验证与结构化企业报告。  
Validate a YonBIP/YonClaw skill before release with general release-convention checks, BIP script auditing, functional coverage review, runtime validation, sensitive-capability auditing, and structured enterprise reporting.

### 完整介绍 / Full Intro

`yonclaw-skill-acceptance` 适合那些需要真实发布结论，而不是随意意见的 YonBIP/YonClaw skill 作者。它会把验收拆成几层：通用规范层关注 `SKILL.md`、`agents/openai.yaml`、触发设计、渐进披露、资源组织、证据纪律和发布适配；BIP 规范层集中检查 `description`、`metadata.yonbip.version`、目录命名、SOP 正文结构、Python 脚本、标准 JSON 输出与异常处理；其余再分别覆盖功能清单、grouped skill 依赖风险、平台集成与运行时行为。除了常规验收，它还会单独暴露命令执行、本地敏感文件访问、动态注入、hooks、隐藏内容与混淆载荷等风险信号。当一次性要筛查多个 skill 时，也支持先做批量分拣，再对高风险或边界结果的 skill 进入深度验收。它要求真实证据，保留待验证项，区分环境噪音与 skill 缺陷，并最终生成一份带发布建议的企业级 Markdown 验收报告，用于 YonClaw 或 ClawHub 发布决策。  
`yonclaw-skill-acceptance` is for YonBIP/YonClaw skill authors who need a real release decision rather than a casual opinion. It separates acceptance into layers: the general-convention layer focuses on `SKILL.md`, `agents/openai.yaml`, trigger design, progressive disclosure, resource organization, evidence discipline, and release readiness; the BIP-compliance layer concentrates `description`, `metadata.yonbip.version`, directory naming, SOP body structure, Python scripts, standard JSON output, and exception handling; the remaining sections cover feature inventory, grouped-skill dependency risk, platform integration, and runtime behavior. Beyond ordinary acceptance, it also surfaces command execution, local sensitive-file access, dynamic injection, hooks, hidden content, and obfuscated payloads as first-class risk signals. When many skills need screening, it can support batch triage first and reserve deep acceptance for risky or boundary-case skills. It requires real evidence, keeps static-only findings distinct from dynamic coverage, separates environment noise from skill defects, and makes permission-to-purpose mismatches visible in the final enterprise-style Markdown acceptance report.
