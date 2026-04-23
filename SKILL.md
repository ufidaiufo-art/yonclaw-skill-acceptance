---
name: yonclaw-skill-acceptance
description: 适用于运行在 YonClaw 中的新建或更新 YonBIP skill 在 YonClaw 内部发布前需要做发布验收的场景。
metadata: {"yonbip":{"version":"1.0.0"}}
---

# YonClaw Skill Acceptance

将此 skill 用作运行在 YonClaw 中的 YonBIP skill 发布门禁。它要求基于真实证据完成规范检查、功能覆盖、动态验证与报告回填。

## 响应契约

在输出任何验收结论之前，必须先确认目标 skill、读取关键文件并收集真实证据。

硬性规则：

- 如果目标缺失，先追问并停在这里
- 如果用户要求在同一轮里“验收并修复”，当前只接受验收部分，拒绝直接修复
- 如果证据不足，不得输出 `通过` 或 `可发布`

固定回复模板：

- missing target:
  - `请先提供要验收的 skill 名称或路径；在目标未确认前，我不会输出验收结论或发布建议。`
- validate-and-fix request:
  - `当前任务只做验收，不直接修改目标 skill。若你需要修复，请在验收完成后单独发起修复任务。`

禁止的捷径行为：

- 未确认目标就直接给出泛化结论
- 没有证据就直接给出 `通过`、`可发布`
- 把静态上“看起来合理”当成动态证据
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
8. `release readiness` 要与“只是能加载”分开判断。
9. 动态测试前先提取目标 skill 的功能清单。
10. 用功能清单驱动 case 覆盖，并显式写出覆盖缺口。
11. 在验收阶段不得修改目标 skill、共享依赖 skill 或业务脚本，除非用户明确切换为修复任务。
12. `static-only` 证据必须与真实动态覆盖在覆盖矩阵和结论中严格区分。
13. 最终输出必须区分业务能力结论与平台集成结论。
14. 敏感能力必须显式审计，不能埋在普通静态检查结论里。
15. 必须显式选择 `single-skill deep acceptance` 或 `batch triage`，不得混用它们的结论。
16. hooks、动态注入、加载即执行命令、隐藏内容和混淆内容都必须作为一等风险信号显式暴露。
17. BIP metadata、命名、SOP 结构以及脚本工程规范都是强制检查项；对 BIP API 型 skill，还要检查是否使用标准共享工具，如 `yonbip_skill_utils.requests` 和 `yonbip_skill_utils.logging`。

## 验收工作流

### 0. 选择验收模式

在读取过多内容前，先决定采用哪种验收模式：

- `single-skill deep acceptance`：对单个目标 skill 做完整的 spec、runtime 和报告级发布验收
- `batch triage`：快速扫描多个 skill，排序风险，并决定哪些需要进入深度验收

规则：

- `batch triage` 可以复用敏感能力和隐藏内容检查，但不能假装自己具备与完整验收相同的深度
- 任何最终发布结论，如 `通过`、`有条件通过`、`不通过`，都必须基于 `deep acceptance`
- `batch triage` 的输出应收束为 shortlist，例如 `needs deep acceptance`、`safe for now` 或 `high-risk`

### 1. 确认验收目标

需要先确认并记录：

- skill 名称
- skill 路径
- 计划使用的 workspace
- 已有验收文档路径（如存在）
- 是否面向 YonClaw 内部发布

如果 skill 位于当前活跃 YonClaw workspace 之外，应创建或使用隔离的验证 workspace，而不是过度改动用户的日常环境。

硬性门禁：

- 不得根据上下文自行猜测一个“可能的目标”
- 在目标确认前，不得输出 pass/fail/release 结论

### 2. 执行静态检查

先做静态检查，确认：

- `SKILL.md` 存在
- frontmatter 包含 `name` 和 `description`
- 引用的脚本或参考文件实际存在
- skill 指令与预期行为一致

### 2a. 执行 spec 检查

目标：确认该 skill 是否符合 BIP 专项编写要求。

必查项：

- `name` 与目录名完全一致
- `metadata` 存在，且是有效的 YAML frontmatter 内容
- `metadata.yonbip.version` 存在，且格式为 `major.minor.patch`
- `description` 以触发条件为导向，最好以 `Use when` 开头
- `description` 关注“何时使用”，而不是冗长的流程摘要
- `description` 明确写出 skill 做什么、用户会怎样提问、可能触发的关键词
- 如果存在 runtime-platform metadata，则内容不能过时或自相矛盾
- `name` 稳定、可读，并在适当场景下采用连字符命名
- 如果 skill 属于独立 skill git 项目，则项目名应符合 BIP 的 `microservice-code-skills` 约定或有文档化等效约定
- 如果 skill 属于独立 skill git 项目，则项目结构应与 BIP 对标准布局的预期一致
- 目录名符合 BIP 命名限制：小写、连字符、无下划线、无双连字符、无前导数字

记录要求：spec 问题必须与 runtime 问题分开记录。

### 2b. 执行通用规范发布审计

目标：确认该 skill 是否达到内部发布要求。

必查项：

- `SKILL.md` 存在，且是 skill 的清晰入口
- 在需要 UI metadata 的场景下，`agents/openai.yaml` 存在、意图一致且不过时
- 被引用的脚本、参考、资源和相关路径实际存在
- trigger 设计清晰，不依赖隐藏假设
- `progressive disclosure` 合理：只要求模型加载真正需要的文件或资源
- 资源组织清晰：`scripts/`、`references/`、`assets/`、`agents/` 分工明确
- 目录洁净：skill 目录中没有不应进入发布包的多余辅助文档
- 证据纪律清晰：没有真实命令输出或 session 证据前，不允许把 case 判成通过
- 失败可见：`pending`、失败项和环境噪音都在报告里保持可见
- 报告完整：默认交付物是结构化报告，而不只是聊天摘要
- 内部发布适配：输出行为、目录洁净度和面向发布的呈现方式适合内部发布
- 不可信输入防护：外部网页或文档内容被当作数据，而不是可执行指令

记录要求：通用规范缺口要与 spec 问题、runtime 问题分开记录。

### 2c. 执行敏感能力审计

目标：识别该 skill 或其引用脚本是否具备敏感能力。

至少检查：

- 系统命令执行，如 `subprocess`、`os.system`、shell 包装器或脚本启动器
- 本地敏感文件访问，如浏览器 cookies、SQLite 数据库、认证缓存、密钥文件或声明范围外的 workspace 文件
- 宽范围网络访问，如任意 URL/path 的 HTTP 请求、通用 API 客户端、代理行为或上传/下载辅助器
- 破坏性或状态改变操作，如 delete/cancel/end/overwrite/bulk update
- 权限不匹配：对外声明能力比实际可达实现能力更弱
- frontmatter 风险因子，如高权限 `allowed-tools`、隐藏调用、lifecycle hooks 或 fork/subprocess 执行模式
- 加载期或触发期命令注入，如动态命令块、自动执行 shell 片段或安装期执行
- 隐藏或混淆内容，如带指令的 HTML 注释、base64 载荷、零宽字符、Unicode 伪装或嵌入式安全覆盖

对每一项敏感能力，都要记录：

- 能力类型
- 发现位置
- 存在原因
- 是否已被 skill 清楚披露
- 是否与声明用途相称
- 是否应允许发布、改为有条件，或直接阻断

记录要求：只要该 skill 具备有意义的能力，就必须显式暴露这种能力。

### 2d. 执行自动执行与隐藏内容检查

目标：检查该 skill 是否会在用户明确调用之前执行或影响行为。

至少检查：

- lifecycle hooks 或平台特定的 auto-run 字段
- skill 加载期执行 shell 或工具命令的动态注入模式
- 规避常规审查的隐藏触发模式
- 改变指令或覆盖安全策略的注释、编码载荷或不可见字符
- 未被清楚披露的 browser cookie、本地数据库或认证缓存访问

记录：

- 该行为是 auto-executed、user-triggered，还是状态不明
- 该行为是否有文档说明
- 该行为是否对声明用途必需
- 该行为是否应该阻断发布

### 2e. 执行异常输入与副作用审计

目标：确认具备写操作能力的 skill 在异常输入、跨平台传参差异或参数解析失败时能够 `fail closed`，不会继续写入错误或残缺业务数据。

适用范围：

- 所有具备 create、update、delete、send、approve、invite、sync 等写操作能力的 skill
- 所有存在脚本调用、CLI/JSON 参数传递、外部工具拼接或多层参数转发的 skill

至少检查：

- 缺少必填参数、参数名错误、空值、类型错误
- 含中文、空格、引号、逗号、多值或歧义参数
- 至少一种非当前主开发环境的调用方式；如适用，优先覆盖 Windows 传参差异
- 从 prompt 到工具调用、命令拼接、脚本解析、最终业务请求的完整参数链路

强制要求：

- 关键参数缺失、解析失败或平台差异导致参数不可信时，必须阻断执行
- 不得静默降级，不得以默认值、占位值或猜测值补齐关键业务字段
- 对所有异常 case，必须追加真实业务回查，不得只依据错误信息、退出码或日志判定安全失败

回查至少确认：

- 是否产生业务记录、半残数据、占位值或错误关联关系
- 关键字段是否完整、准确、可解释，包括适用的 ID、姓名、参与人、时间范围、数量、状态和关联关系

判定规则：

- 若异常输入导致任何脏数据落库，结论不得为 `通过`
- 若异常输入可能污染核心业务对象，结论应为 `不通过`
- 主流程可用但异常路径未覆盖时，结论最多为 `有条件通过`
- 对适用 skill，未执行本章节时，不得输出 `通过` 或 `可发布`

### 3. 执行平台集成检查

使用与当前验证环境匹配的运行平台命令。

```bash
<runtime-platform-refresh-command>
<runtime-platform-list-command>
<runtime-platform-info-command> <skill-name>
```

通过标准：

- 运行平台能够成功刷新或重载
- skill 能在运行平台中被发现
- 运行平台的 info 或 metadata 命令解析到预期目录和文件集

如果 YonClaw 当前没有使用目标 workspace，要在报告中记录这一事实；如有必要，可临时切换到隔离的验证 workspace，并记录实际使用的路径。

### 3a. 提取功能清单

在开始动态测试前，先读取目标 skill，并从显式功能清单、能力 bullet、操作动词、guardrail/输出规则以及引用脚本中提取功能清单。

对每个 feature，至少记录：

- feature id
- feature name
- 在 skill 文件或引用资源中的来源证据
- feature category（如 `core operation`、`guardrail`、`branch behavior`、`output rule`、`integration requirement`、`BIP compliance requirement`）
- 该 feature 的动态验证是 required、optional，还是被环境阻塞

不要把一个 happy path 的成功当成所有声明功能都可用的证明。

### 3b. 建立覆盖矩阵

在动态验证前，先建立 feature-to-case 覆盖矩阵。

至少使用这些状态：`covered by dynamic case`、`covered by static/spec evidence only`、`pending due to environment or prerequisite gap`、`blocked by environment or platform failure`、`out of scope for this round`。

只有在证据仍然明确且无歧义时，才允许用一个 case 覆盖多个相近 feature。

### 4. 执行动态行为检查

至少验证 `Positive`、`Negative`、`Incomplete input`、`Safety` 四类基线 prompt；如该 skill 存在按操作分支的行为，还需补充分支定向 case。无法安全执行的操作保持为 `pending` 或 `blocked`，并记录阻塞原因。

基线 prompt 的硬门禁：

- `Positive` 必须体现真实验收行为，而不是输出一段泛化的“可发布”摘要
- `Incomplete input` 必须追问缺失的目标 skill 或前置条件，而不是凭空补成成功
- `Safety` 必须明确拒绝“边验收边修复”，只能继续做验收，或停下来询问是否在验收后单独开启修复任务
- 如果缺少动态证据，就保持 case 为 `pending` 或 `blocked`，不得升级为 `pass`

### 4a. 执行 BIP 脚本合规检查

如果目标 skill 包含 `scripts/`，至少检查：

- 脚本是否采用 Python，而不是在没有充分理由的情况下混用任意运行时
- 脚本名是否符合 lowercase underscore 风格
- BIP API 访问是否使用 `yonbip_skill_utils.requests` 或有文档化等效封装
- 日志是否使用 `yonbip_skill_utils.logging` 或有文档化等效方案
- 最终脚本输出是否为 JSON，且至少包含 `success` 和 `message`
- 异常是否被标准化输出，而不是直接抛原始异常

这些结果要与动态业务行为分开记录。

### 5. 评估真实行为，而不只是看是否触发

不要只看有没有触发 skill，还要检查模型是否真的遵守了 skill 规则与输出约束。

需要显式标记的失败模式：

- 没有 file、command 或 session 证据，却输出泛化的“通过”或“可发布”
- 缺参 prompt 被回答成“目标已经知道”
- `Safety` prompt 下悄悄接受或暗示在验收中直接修复

### 5a. 评估覆盖完整性

动态测试后，反向核对功能清单：哪些声明功能已被动态覆盖，哪些只有静态证据，哪些仍是 `pending`，哪些被环境阻塞，哪些关键功能仍未验证。

如果关键声明功能仍未被验证，就不要标记为 `通过`，除非用户明确缩小了本轮范围，并且该范围收缩已被记录。

### 5b. 可选的第二意见复核

当风险等级仍然模糊、结论接近 pass/fail 边界，或用户明确要求 cross-validation 时，可追加第二意见复核。第二意见只能作为辅助证据，不能覆盖代码或 runtime 行为中的直接证据。

### 6. 回填验收记录

将执行摘要、关键检查结果、覆盖矩阵、真实证据、环境问题、结论和发布建议回填到验收文档中。若无现成文档，则使用 `assets/enterprise-acceptance-report-template.md` 创建新报告。已执行项填充真实证据，未执行项保持为 `pending` 或 `blocked`，最终 verdict 必须拆成业务能力结论和平台集成结论。

结论门禁：

- 目标从未被明确确认时，不得输出 `通过` 或 `适合发布...`
- 没有发生基于证据的真实验收执行时，不得输出 `通过` 或 `适合发布...`
- 如果证据不完整，应根据情况优先给出 `有条件通过`、`不通过`、`pending` 或 `blocked`
- 如果请求本身不完整，就不要输出任何发布结论；先追问缺失目标

推荐发布建议状态：

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
- 把 spec、通用规范和 runtime 问题分开
- 总结声明功能的覆盖情况，而不只是统计 case 数量
- 保持未解决项可见
- 单独总结环境注意事项
- 确认报告文件已写出；若未写出，必须明确说明原因
- 说明该 skill 当前是适合内部发布、需要继续测试，还是需要修复
