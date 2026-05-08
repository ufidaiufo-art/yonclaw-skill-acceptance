---
name: yonclaw-skill-acceptance
description: "Use when a new or updated YonBIP skill running in YonClaw needs release validation before YonClaw internal rollout. 触发词：验收、发布验收、skill验收、YonClaw验收、发布门禁、release validation、acceptance、acceptance test、验收测试、回归检查"
metadata: {"yonbip":{"version":"1.0.0"}}
allowed-tools:
  - Read
  - Bash
  - Write
  - Edit
  - Glob
  - Grep
---

# YonClaw Skill Acceptance

> **TL;DR** — 本 skill 是 YonClaw 中 YonBIP skill 的发布门禁。6步走：① 确认目标 → ② 静态/spec/规范/敏感能力/隐藏内容/异常输入检查 → ③ 平台集成（`yonclaw refresh/list/info`）+ 强制读取 + 功能清单 + 覆盖矩阵 → ④ 动态行为验证（Positive/Negative/Incomplete/Safety）→ ⑤ 覆盖完整性评估 + 检查点全集 + 报告自检纠偏 → ⑥ 回填 Excel 报告（4页签含检查点自检；Markdown 可选）。分阶段 gated output：skill-info.json → checkpoints-covered.json → test-results.json → validate_checkpoints.mjs → Excel 报告 → validate_excel_report.mjs。默认 Excel 交付；Markdown 需用户明确要求且必须通过自动合规校验。

将此 skill 用作运行在 YonClaw 中的 YonBIP skill 发布门禁。它要求基于真实证据完成规范检查、功能覆盖、动态验证与报告回填。

## 响应契约

在输出任何验收结论之前，必须先确认目标 skill、读取关键文件并收集真实证据。

硬性规则：

- 如果目标缺失，先追问并停在这里
- 如果用户要求在同一轮里"验收并修复"，当前只接受验收部分，拒绝直接修复
- 如果证据不足，不得输出 `通过` 或 `可发布`

固定回复模板：

- missing target:
  - `请先提供要验收的 skill 名称或路径；在目标未确认前，我不会输出验收结论或发布建议。`
- validate-and-fix request:
  - `当前任务只做验收，不直接修改目标 skill。若你需要修复，请在验收完成后单独发起修复任务。`

禁止的捷径行为：

- 未确认目标就直接给出泛化结论
- 没有证据就直接给出 `通过`、`可发布`
- 把静态上"看起来合理"当成动态证据
- 在验收过程中默默接受修复工作

## 适用场景

- 新建了一个 YonBIP skill，需要做发布前验收。
- 一个已有 skill 被修改过，需要做回归检查。
- 需要基于证据判断该 skill 是否适合 YonClaw 内部发布。
- 需要看到运行平台证据、真实 prompt 结果和结构化验收报告。

不要将此 skill 用于与 YonBIP 或 YonClaw skill 无关的普通 prompt 测试。

## 核心规则

1. 将 spec 检查、静态检查、通用规范检查、功能清单检查和动态检查严格分开记录。
2. 运行平台可发现是必要条件，但绝不是充分条件。
3. 只要场景适用，至少要跑一个 `Positive`、一个非触发 case 和一个 `Safety` case。
4. 没有真实命令输出或真实 session 结果，就不能把 case 判成 `pass`。
5. 未执行项保持为 `pending` 或 `blocked`，不要在最终总结时升级成已覆盖。
6. 环境噪音要与 skill 行为分开记录。
7. 即使 skill 能加载，spec 问题也必须单独记录。
8. `release readiness` 要与"只是能加载"分开判断。
9. 执行验收前必须完整读取目标 skill 的 `SKILL.md`，并读取其直接引用的 `tool_schema.json`、`scripts/`、`references/`、`agents/openai.yaml`、`assets/` 模板或其他本地文件；未完成读取前不得生成验收报告。
10. 动态测试前先提取目标 skill 的功能清单。
11. 用功能清单驱动 case 覆盖，并显式写出覆盖缺口。
12. 在验收阶段不得修改目标 skill、共享依赖 skill 或业务脚本，除非用户明确切换为修复任务。
13. `static-only` 证据必须与真实动态覆盖在覆盖矩阵和结论中严格区分。
14. 最终输出必须区分业务能力结论与平台集成结论。
15. 敏感能力必须显式审计，不能埋在普通静态检查结论里。
16. 必须显式选择 `single-skill deep acceptance` 或 `batch triage`，不得混用它们的结论。
17. hooks、动态注入、加载即执行命令、隐藏内容和混淆内容都必须作为一等风险信号显式暴露。
18. BIP metadata、命名、SOP 结构以及脚本工程规范都是强制检查项；对 BIP API 型 skill，还要检查是否使用标准共享工具，如 `yonbip_skill_utils.requests` 和 `yonbip_skill_utils.logging`。⚠️ 已知缺陷：部分 skill 中 `yonbip_skill_utils.logging` 虽被引用但未实际使用（日志未写入或未格式化），检查时应验证日志是否真正产出，而非仅检查 import 语句。
19. 当用户要求 Markdown 企业报告时，必须保留 `assets/enterprise-acceptance-report-template.md` 的关键表格字段；只复制章节标题、把功能清单/覆盖矩阵/动态用例结果简化成摘要，视为未使用模板。
20. `READ` 功能不得用不可逆、无法回滚、污染生产数据或需确认等写操作风险作为 blocked 理由；这些理由只适用于真实 `WRITE / STATE` 风险。
21. 当用户要求 Markdown 企业报告时，`11.3 自动合规校验` 必须回填最后一次校验结果；Markdown 报告不得保留首次失败的 `FAIL` 或在 `10.4.1` 将校验器写成 `N/A`。
22. 当用户要求 Markdown 企业报告时，`11.3` 若结果不是 `FAIL`，`失败项` 必须为 `无`；旧 error code、旧失败说明或 warning 不得残留在失败项中。
23. 当用户要求 Markdown 企业报告时，`10.4.1` 不得把校验器状态写成 `模板待运行`、`需运行校验器`、`待重新校验` 等未完成表述；Markdown 报告只能记录最后一次已完成校验。
24. `Baseline Failure` 是条件门禁，只对问题修复类、回归类或重大行为变更类验收强制要求。首次上架的新 skill 若没有历史失败问题、旧版本或复现材料，应标记为 `not applicable` 或 `未执行`，不得因此阻断发布，也不得臆造 baseline failure。
25. 验收完成后的默认正式报告格式是 Excel；只有用户明确要求 Markdown、企业验收文档、`.md`、或需要回填既有 Markdown 验收文档时，才额外输出 Markdown 报告。
26. 同一轮同时验收多个 skill 时，只输出一份合并 Excel 汇总报告；不要为每个 skill 分别输出独立 Excel。Markdown 报告仍然只有在用户明确要求时才输出。
27. **阶段产物门禁**：验收必须先写 `skill-info.json`、`checkpoints-covered.json`、`test-results.json`，三者都存在且通过 `scripts/validate_checkpoints.*` 后才允许生成报告；细则见 `references/staged-artifacts.md`。
28. **报告交付门禁（三级降级）**：报告按 Node.js Excel → Python Excel → Markdown 降级，不得跳级；生成后必须运行对应校验脚本；细则见 `references/report-generation-rules.md`。
29. **检查点全集自检门禁**：生成报告前必须以 `assets/checkpoints.json` 建立检查点全集；生成后必须逐项自检和纠偏；细则见 `references/report-generation-rules.md`。

## 错误恢复策略

详细恢复规则见 `references/error-recovery.md`。

验收各阶段失败时的恢复动作必须按该文件执行，并在报告中记录：`原失败点 | 恢复动作 | 恢复结果 | 对结论的影响`。

## 验收工作流

### 0. 选择验收模式

在读取过多内容前，先决定采用哪种验收模式：

- `single-skill deep acceptance`：对单个目标 skill 做完整的 spec、runtime 和报告级发布验收
- `batch triage`：快速扫描多个 skill，排序风险，并决定哪些需要进入深度验收

规则：

- `batch triage` 可以复用敏感能力和隐藏内容检查，但不能假装自己具备与完整验收相同的深度
- 任何最终发布结论，如 `通过`、`有条件通过`、`不通过`，都必须基于 `deep acceptance`
- `batch triage` 的输出应收束为 shortlist，例如 `needs deep acceptance`、`safe for now` 或 `high-risk`

### 0a. 分阶段 gated output

执行本阶段前必须读取 `references/staged-artifacts.md`。

验收必须落地三类阶段产物：`skill-info.json`、`checkpoints-covered.json`、`test-results.json`。默认输出目录为当前 workspace 的 `assets/<skill-name>-acceptance/`；用户指定目录时按用户目录写入。

硬门禁：

- 三类阶段产物缺一不可
- `skill-info.json` 必须记录目标 skill、已读文件和功能清单
- `checkpoints-covered.json` 必须基于 `assets/checkpoints.json` 并追加目标 feature 检查点
- `test-results.json` 必须记录 `positive`、`negative`、`incomplete_input`、`safety` 四类基线 case
- 必须运行 `scripts/validate_checkpoints.mjs` 或 `scripts/validate_checkpoints.py`
- 校验失败时只能修正阶段产物，不得绕过校验生成报告
- 最终回复必须给出三个阶段产物路径、校验命令和校验结果

### 1. 确认验收目标

需要先确认并记录：

- skill 名称
- skill 路径
- 计划使用的 workspace
- 已有验收文档路径（如存在）
- 是否面向 YonClaw 内部发布

如果 skill 位于当前活跃 YonClaw workspace 之外，应创建或使用隔离的验证 workspace，而不是过度改动用户的日常环境。

硬性门禁：

- 不得根据上下文自行猜测一个"可能的目标"
- 在目标确认前，不得输出 pass/fail/release 结论

**输出门禁**：阶段1完成前必须产出一个结构化的目标确认记录，包含上述5项；任何一项为空时，该阶段状态为 `pending`，不得进入阶段2。

### 2. 执行静态检查

先做静态检查，确认：

- `SKILL.md` 存在
- frontmatter 包含 `name` 和 `description`
- 引用的脚本或参考文件实际存在
- skill 指令与预期行为一致

### 2a. 执行 spec 检查

执行前必须读取 `references/audit-rules.md` 的 Spec 检查规则。

目标：确认目标 skill 是否符合 BIP 专项编写要求。spec 问题必须与 runtime 问题分开记录。

**输出门禁**：阶段2a完成前必须产出 spec 检查结果清单，每条记录包含 `检查项 | 结果 | 证据位置`；无空字段，无省略号占位。

### 2b. 执行通用规范发布审计

执行前必须读取 `references/audit-rules.md` 的通用规范发布审计规则。

目标：确认目标 skill 是否达到内部发布要求。通用规范缺口要与 spec 问题、runtime 问题分开记录。

**输出门禁**：阶段2b完成前必须产出通用规范审计结果清单，每条记录包含 `检查项 | 结果 | 证据位置`；无空字段。

### 2c. 执行敏感能力审计

执行前必须读取 `references/audit-rules.md` 的敏感能力审计规则。

目标：识别目标 skill 或其引用脚本是否具备系统命令、本地敏感文件、宽范围网络、破坏性写操作、高权限 frontmatter、加载期执行或隐藏混淆内容等敏感能力。只要存在有意义的敏感能力，就必须显式暴露。

**输出门禁**：阶段2c完成前必须产出敏感能力清单，每条包含 `能力类型 | 发现位置 | 存在原因 | 是否披露 | 是否相称 | 发布建议`；零敏感项时须显式写 `无敏感能力`，不得省略。

### 2d. 执行自动执行与隐藏内容检查

执行前必须读取 `references/audit-rules.md` 的自动执行与隐藏内容检查规则。

目标：检查目标 skill 是否会在用户明确调用之前执行或影响行为，或是否存在规避审查的隐藏触发、编码载荷、不可见字符或未披露认证缓存访问。

**输出门禁**：阶段2d完成前必须产出自动执行/隐藏内容检查结果，每条包含 `行为描述 | 触发方式(auto/user/不明) | 是否文档化 | 是否必需 | 阻断发布(是/否)`；无异常时须显式写 `无自动执行或隐藏内容`，不得省略。

### 2e. 执行异常输入与副作用审计

执行前必须读取 `references/audit-rules.md` 的异常输入与副作用审计规则。

目标：确认具备写操作、脚本调用或多层参数转发的 skill 在异常输入、跨平台传参差异或参数解析失败时能够 `fail closed`，不会继续写入错误或残缺业务数据。

硬门禁：

- 关键参数缺失、解析失败或平台差异导致参数不可信时，必须阻断执行
- 不得用默认值、占位值或猜测值补齐关键业务字段
- 异常 case 必须追加真实业务回查
- 异常输入导致脏数据落库时，结论不得为 `通过`
- 适用 skill 未执行本章节时，不得输出 `通过` 或 `可发布`

**输出门禁**：阶段2e完成前必须产出异常输入审计结果，每条包含 `异常场景 | 输入构造 | 执行结果 | 是否产生脏数据 | 结论(通过/有条件通过/不通过)`；该 skill 不具备写操作能力时，须显式写 `不适用（无写操作能力）`。

### 3. 执行平台集成检查

使用与当前验证环境匹配的运行平台命令。

```bash
yonclaw refresh
yonclaw list
yonclaw info <skill-name>
```

通过标准：

- 运行平台能够成功刷新或重载
- skill 能在运行平台中被发现
- 运行平台的 info 或 metadata 命令解析到预期目录和文件集

如果 YonClaw 当前没有使用目标 workspace，要在报告中记录这一事实；如有必要，可临时切换到隔离的验证 workspace，并记录实际使用的路径。

**输出门禁**：阶段3完成前必须记录 `yonclaw refresh`、`yonclaw list`、`yonclaw info <skill-name>` 三条命令的真实输出；任何一条未执行时，本阶段状态为 `pending`。

### 3a. 强制读取目标 skill

在生成测试点或输出验收报告前，必须完整读取目标 skill 的 `SKILL.md`。

如果 `SKILL.md` 直接引用了以下文件或目录，必须继续读取对应内容后再生成测试点：

- `tool_schema.json`
- `scripts/` 下被声明为入口或工具的脚本
- `references/` 下被 `SKILL.md` 或 schema 直接引用的文档
- `agents/openai.yaml`
- `assets/` 下被报告、模板或输出规则直接引用的文件
- 其他被 `SKILL.md` 明确点名的本地文件

读取完成后，必须先提取：

- 功能清单
- 输入参数与输出规则
- 写入或状态改变能力
- 安全风险点
- 依赖的外部平台或真实数据接口
- 文档中声明的不支持能力与 guardrail

Excel 明细中的每个测试点必须来自上述提取结果或验收方法论固定检查项。未完整读取目标 skill 和直接引用文件前，不得生成验收报告。

### 3b. 提取功能清单

在开始动态测试前，从显式功能清单、能力 bullet、操作动词、guardrail/输出规则以及引用脚本中提取功能清单。

对每个 feature，至少记录：

- feature id
- feature name
- 在 skill 文件或引用资源中的来源证据
- feature category（如 `core operation`、`guardrail`、`branch behavior`、`output rule`、`integration requirement`、`BIP compliance requirement`）
- 该 feature 的动态验证是 required、optional，还是被环境阻塞

不要把一个 happy path 的成功当成所有声明功能都可用的证明。

**输出门禁**：阶段3b完成前必须产出功能清单表格，每行包含 `feature id | feature name | 来源证据 | feature category | 动态验证要求(required/optional/blocked)`；清单不得为空（至少包含 skill 声明的核心能力）。

### 3c. 记录 baseline failure 证据

`Baseline Failure` 用来证明本轮变更确实修复了一个历史失败或行为缺口。它不是所有 skill 的通用硬门禁。

适用范围：

- 已有 skill 的问题修复或回归验收：必须记录 baseline failure
- 重大行为变更：必须记录旧行为与新行为差异
- 批量验收：只记录是否存在历史问题来源，不强制逐个复现
- 首次上架的新 skill：默认不适用，除非用户提供了明确的历史失败场景或竞品/旧方案失败证据

至少记录：

- 压力 prompt 或场景
- 旧 skill、无 skill 或未改造前的实际行为
- 应用 skill 后的期望行为
- 关闭该缺口的具体规则或章节

如果旧版本不可用、环境不可复现、没有历史问题单、没有用户复现材料，或目标是首次上架的新 skill，标记为 `not applicable`、`not reproducible`、`pending` 或 `out-of-scope`，并说明原因。不得根据经验臆造 baseline failure。

该证据用于证明修复或行为变更的有效性，不能替代动态验收、平台发现、业务回查或功能覆盖证据。对不适用 baseline 的首次上架 skill，发布判断应依赖 spec、静态检查、功能覆盖、动态用例、安全审计和真实证据。

**输出门禁**：阶段3c完成前必须产出 baseline failure 记录，包含 `压力prompt/场景 | 旧行为 | 期望行为 | 缺口关闭规则`；无法复现时须写明原因，不得留空；首次上架新 skill 标记为 `not applicable`。

### 3d. 建立覆盖矩阵

在动态验证前，先建立 feature-to-case 覆盖矩阵。

至少使用这些状态：`covered by dynamic case`、`covered by static/spec evidence only`、`pending due to environment or prerequisite gap`、`blocked by environment or platform failure`、`out of scope for this round`。

对于 `WRITE / STATE / SPECIAL` 功能，缺参、缺确认、`success=false` 或错误阻断用例只能覆盖异常输入/防护行为，不能把该业务功能标记为 `covered`。只有正常执行、业务系统回查和必要的清理/恢复都完成后，才能把对应业务功能标记为动态 covered。

只有在证据仍然明确且无歧义时，才允许用一个 case 覆盖多个相近 feature。

**输出门禁**：阶段3d完成前必须产出覆盖矩阵，每行包含 `feature id | feature name | 覆盖状态 | 覆盖证据来源`；所有功能清单中的 feature id 必须在矩阵中出现，不得遗漏。

### 4. 执行动态行为检查

至少验证 `Positive`、`Negative`、`Incomplete input`、`Safety` 四类基线 prompt；如该 skill 存在按操作分支的行为，还需补充分支定向 case。无法安全执行的操作保持为 `pending` 或 `blocked`，并记录阻塞原因。具体 prompt 示例见 `references/prompt-examples.md`，agent 应根据目标 skill 的实际能力调整。

基线 prompt 的硬门禁：

- `Positive` 必须体现真实验收行为，而不是输出一段泛化的"可发布"摘要
- `Incomplete input` 必须追问缺失的目标 skill 或前置条件，而不是凭空补成成功
- `Safety` 必须明确拒绝"边验收边修复"，只能继续做验收，或停下来询问是否在验收后单独开启修复任务
- 如果缺少动态证据，就保持 case 为 `pending` 或 `blocked`，不得升级为 `pass`

**输出门禁**：阶段4完成前必须产出四类基线用例结果，每条包含 `用例类型 | prompt摘要 | 执行结果 | 证据引用`；四类（Positive/Negative/Incomplete/Safety）缺一不可，未执行的写明阻塞原因。

### 4a. 执行 BIP 脚本合规检查

执行前必须读取 `references/audit-rules.md` 的 BIP 脚本合规检查规则。

如果目标 skill 包含 `scripts/`，必须检查脚本运行时、命名、BIP API 访问封装、日志、JSON 输出、异常标准化和每个入口脚本的单测/手工执行证据。脚本合规结果要与动态业务行为分开记录。

**输出门禁**：阶段4a完成前必须产出脚本合规检查结果，每条包含 `检查项 | 结果(pass/fail/N/A) | 证据`；目标 skill 无 `scripts/` 时写 `不适用（无脚本目录）`；有 `scripts/` 时必须额外包含单测执行结果列（`脚本入口 | 单测/执行结果 | 证据`），无测试证据的脚本行必须标记为 `fail`。

### 5. 评估真实行为，而不只是看是否触发

不要只看有没有触发 skill，还要检查模型是否真的遵守了 skill 规则与输出约束。

需要显式标记的失败模式：

- 没有 file、command 或 session 证据，却输出泛化的"通过"或"可发布"
- 缺参 prompt 被回答成"目标已经知道"
- `Safety` prompt 下悄悄接受或暗示在验收中直接修复

### 5a. 评估覆盖完整性

动态测试后，反向核对功能清单：哪些声明功能已被动态覆盖，哪些只有静态证据，哪些仍是 `pending`，哪些被环境阻塞，哪些关键功能仍未验证。

默认执行规则：

- 只要功能有 `prompt`、`script/api`、`pytest` 或等价可执行入口，验收时默认必须执行。
- 只有存在明确阻塞原因时，才能不执行并标记为 `blocked`、`skipped`、`out-of-scope` 或带原因的 `pending`。
- 验收技能被调用时默认验收环境已经准备好，`缺少环境`、`缺少权限`、`认证不可用`、`跨平台环境不可用`、`后续再测` 不得作为跳过执行的理由。
- 可接受的阻断原因仅限：用户明确缩小本轮范围、用户明确拒绝执行某个高风险动作、动作不可逆且无法回滚、执行会污染生产数据且没有隔离测试数据。
- 不可接受的原因包括：时间不足、只做基线验收、脚本存在、静态确认、无测试环境、无权限、认证失败、后续再测。
- 未执行的可执行功能必须在覆盖矩阵和后续动作中写清 feature id、阻塞原因和补验条件。

如果关键声明功能仍未被验证，就不要标记为 `通过`，除非用户明确缩小了本轮范围，并且该范围收缩已被记录。

**输出门禁**：阶段5a完成前必须产出更新后的覆盖矩阵（动态验证后的最终版本），`pending` 和 `blocked` 项须有明确阻塞原因；未覆盖功能数 > 0 时，结论不得为 `通过`。

### 5b. 可选的第二意见复核

当风险等级仍然模糊、结论接近 pass/fail 边界，或用户明确要求 cross-validation 时，可追加第二意见复核。第二意见只能作为辅助证据，不能覆盖代码或 runtime 行为中的直接证据。

### 5c. 生成检查点全集

执行前必须读取 `references/report-generation-rules.md` 的检查点全集规则。

生成报告前，必须先建立本轮验收的检查点全集。固定方法论检查点以 `assets/checkpoints.json` 为唯一来源；目标 skill 派生检查点必须来自 `SKILL.md`、`tool_schema.json`、引用脚本和参考文档中的声明能力。

硬门禁：

- 每个声明 feature 至少生成一条 `FEATURE-*` 或 `DYNAMIC-*` 明细测试点
- 不能动态验证时，必须标记为 `未执行` 或 `阻塞` 并写明原因
- `适用-未覆盖`、`未执行`、`阻塞` 必须出现在风险、未决项或后续动作中
- 写入 `checkpoints-covered.json` 时必须使用 `references/report-generation-rules.md` 中定义的状态映射

### 5d. 报告生成后强制自检

执行前必须读取 `references/report-generation-rules.md` 的报告自检与纠偏规则。

写出 Excel 或 Markdown 报告后，必须逐项核对检查点全集，并确认目标 skill 派生 feature、固定方法论检查点、未执行/阻塞原因、报告自检页签和汇总统计全部一致。

硬门禁：

- 自检发现漏项时，必须先补报告或降级结论，再重新自检
- TARGET/READ/VERDICT/REPORT 自检项不得计入目标 skill 明细通过率
- 覆盖位置不得写成 `见报告`、`已覆盖` 等泛化描述
- 证据不足但结论过高时，必须降级业务能力结论、平台集成结论或发布建议
- 最多允许 3 轮纠偏；仍未闭环时，报告状态必须标记为 `阻塞` 或 `不通过`

### 6. 回填验收记录

执行前必须读取 `references/report-generation-rules.md`。若用户要求 Markdown，还必须读取 `references/report-compliance-rules.md`。

默认生成 Excel 汇总报告。Excel 必须从 `skill-info.json`、`checkpoints-covered.json`、`test-results.json` 生成；如果报告内容与阶段产物冲突，以阶段产物为准修正报告。

硬门禁：

- 不得只输出会话内摘要报告
- 报告必须按 Node.js Excel → Python Excel → Markdown 的三级降级策略生成
- 生成后必须运行对应校验脚本
- 降级时必须在报告中记录降级原因
- Excel 至少包含 `汇总`、`<skill-name>汇总`、`<skill-name>`、`检查点自检` 4 个页签
- 报告自检项不得写入目标 skill 明细页或计入测试点统计
- Markdown 仅在用户明确要求或 Excel 完全不可用时生成
- Markdown 必须使用企业报告模板结构，并通过 `scripts/validate_report.py`
- 自动校验失败时，报告无效；必须先修正报告或降级结论再重新校验
- Excel 报告最终结论不得高于 `references/report-generation-rules.md` 允许的最高结论；Markdown 报告最终结论还不得高于 `references/report-compliance-rules.md` 允许的最高结论

推荐发布建议状态只使用：

- `适合 YonClaw 内部发布`
- `修复后再发布`

### `batch triage` 最低输出要求

如果执行的是 `batch triage` 而不是 `deep acceptance`，输出至少要包含：skill 名称、声明用途、来源 / 位置、当前最高风险等级、是否需要 `deep acceptance`，以及基于证据的简明原因。

## 最小用例集

除非该 skill 需要更多 case，否则默认使用 `Positive`、`Negative`、`Incomplete-input`、`Safety` 四类基线用例；必要时再补 `Boundary case`、`Error-input` 或操作族定向用例。

## 证据标准

有效证据通常包括：对 skill 文件及相关行号的直接引用、runtime platform discovery/info 输出、真实 runtime agent 结果、作为环境说明记录下来的 gateway 或 runtime warning、从已执行 case 到声明 feature 的直接映射，以及在适用时能直接证明 `metadata.yonbip.version`、SOP 结构、脚本输出形状与异常处理行为的证据。

不要把主观假设、静态阅读或推断行为当成动态证据。

## 收尾检查

收尾前，确认以下事项：

- 确认真正执行过哪些 case
- 确认 `skill-info.json`、`checkpoints-covered.json`、`test-results.json` 已写出
- 确认 `scripts/validate_checkpoints.mjs` 或 `scripts/validate_checkpoints.py` 已通过；若未通过，不得生成或交付报告
- 确认检查点全集已经生成，并在 `检查点自检` 页签逐项核对
- 确认所有适用检查点都已覆盖，或以 `未执行`、`阻塞`、`不适用` 形式带原因保留
- 把 spec、通用规范和 runtime 问题分开
- 总结声明功能的覆盖情况，而不只是统计 case 数量
- 保持未解决项可见
- 单独总结环境注意事项
- 确认报告已按三级降级策略生成：Node.js Excel → Python Excel → Markdown
- 确认报告校验已通过（对应优先级的校验脚本）；若未通过，不得交付为合格报告
- 若发生降级，确认降级原因已记录在报告中
- 若用户要求 Markdown，确认 Markdown 报告文件已写出并通过自动合规校验；若未写出或未校验，必须明确说明原因
- 说明该 skill 当前是适合内部发布、需要继续测试，还是需要修复

**输出门禁**：阶段6完成前必须确认报告已按三级降级策略生成且校验通过（Excel 至少4个页签含检查点自检、表头完整；Markdown 须通过 `validate_report.py` 校验）；`validate_checkpoints.mjs` 或 `validate_checkpoints.py` 已通过；若发生降级，降级原因须记录在报告中；任一交付物未完成时须明确写出原因和后续动作。

## 输出质量自检清单

在输出最终验收结论之前，必须逐项完成 `references/output-quality-checklist.md` 中的 Q1-Q12 自检。任何一项不通过时，不得输出 `通过` 或 `适合 YonClaw 内部发布`。自检结果必须在验收报告的收尾部分呈现，格式为：`自检项 | 结果(通过/不通过) | 说明`。
