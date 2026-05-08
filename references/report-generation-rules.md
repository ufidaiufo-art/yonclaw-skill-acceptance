# Report Generation Rules

本文件定义验收报告生成、自检、纠偏和结论一致性规则。生成 Excel 或 Markdown 报告前必须读取本文件。

## 资源解析

- `references/report-compliance-rules.md`、`assets/enterprise-acceptance-report-template.md`、`assets/checkpoints.json`、`scripts/validate_report.py`、`scripts/validate_checkpoints.*`、`scripts/validate_excel_report.*` 都属于 **yonclaw-skill-acceptance 验收技能目录**，不是被验收的目标 skill 目录。
- 读取这些文件时，先按当前验收技能目录解析相对路径。
- 若运行时无法确定相对路径，优先检查 `~/.agents/skills/yonclaw-skill-acceptance/` 和当前 runtime 中的 `openclaw/skills/yonclaw-skill-acceptance/`。
- 只有这些验收技能目录都不存在对应资源时，才说明资源缺失；不得因为目标 skill 目录没有 `references/` 或 `assets/` 就认为模板缺失。

## 检查点全集

生成报告前必须建立本轮验收的检查点全集。固定方法论检查点以 `assets/checkpoints.json` 为唯一来源，不得手工删减模板项。

检查点全集由两部分组成：

- 固定方法论检查点：TARGET、READ、SPEC、GENERAL、PLATFORM、FEATURE、DYNAMIC、SCRIPT、SECURITY、SIDE、BASELINE、VERDICT、REPORT
- 目标 skill 派生检查点：来自 `SKILL.md`、`tool_schema.json`、引用脚本和参考文档中的声明能力

每个声明 feature 至少生成一条 `FEATURE-*` 或 `DYNAMIC-*` 明细测试点。不能动态验证时，必须标记为 `未执行` 或 `阻塞` 并写明原因。

状态映射：

- `适用-已覆盖` -> `covered`
- `适用-未覆盖` -> `failed`
- `不适用` -> `not_applicable`
- `未执行` -> `skipped`
- `阻塞` -> `blocked`

`适用-未覆盖`、`未执行`、`阻塞` 必须出现在风险、未决项或后续动作中。

## 报告生成三级降级

默认生成 Excel 汇总报告。Excel 是正式交付物，必须从 `skill-info.json`、`checkpoints-covered.json`、`test-results.json` 生成，不得凭聊天上下文重写。

优先级 1：Node.js Excel。

```bash
cd <yonclaw-skill-acceptance>/scripts && npm install
node <yonclaw-skill-acceptance>/scripts/generate_report.mjs \
  --skill-info <output-dir>/skill-info.json \
  --checkpoints <output-dir>/checkpoints-covered.json \
  --test-results <output-dir>/test-results.json \
  --output <output-dir>/<skill-name>-acceptance-report.xlsx
node <yonclaw-skill-acceptance>/scripts/validate_excel_report.mjs \
  <output-dir>/<skill-name>-acceptance-report.xlsx \
  --checkpoints <output-dir>/checkpoints-covered.json
```

优先级 2：Python Excel。

```bash
python3 <yonclaw-skill-acceptance>/scripts/generate_report.py \
  --skill-info <output-dir>/skill-info.json \
  --checkpoints <output-dir>/checkpoints-covered.json \
  --test-results <output-dir>/test-results.json \
  --output <output-dir>/<skill-name>-acceptance-report.xlsx
python3 <yonclaw-skill-acceptance>/scripts/validate_excel_report.py \
  <output-dir>/<skill-name>-acceptance-report.xlsx \
  --checkpoints <output-dir>/checkpoints-covered.json
```

优先级 3：Markdown。仅当 Excel 生成能力完全不可用，或用户明确要求 Markdown 时使用。Markdown 报告必须运行：

```bash
python3 <yonclaw-skill-acceptance>/scripts/validate_report.py <report-path>
```

降级时必须在报告中记录降级原因。降级不影响验收结论有效性，但 Markdown 不包含检查点自检页签，需在正文补充自检结果。

## 默认输出路径

- 单 skill Excel：目标 skill 的 `assets/<skill-name>-acceptance-report.xlsx`
- 目标 skill 不可写时：当前 workspace 的 `assets/`
- 多 skill Excel：当前 workspace 的 `assets/yonclaw-skills-acceptance-report.xlsx`
- 用户明确要求 Markdown：目标 skill 的 `assets/<skill-name>-acceptance-report.md`；不可写时写入当前 workspace 的 `assets/`

## Excel 格式门禁

Excel 报告至少包含 4 个页签：

- `汇总`
- `<skill-name>汇总`
- `<skill-name>` 明细
- `检查点自检`

Excel 字段规范详见 `assets/excel-field-constraints.md`。关键枚举：

- 明细页 `测试结果`：`通过`、`不通过`、`未执行`
- 检查点自检 `自检结果`：`通过`、`未通过`、`阻塞`、`不适用`

`目标确认`、`强制读取`、`结论门禁`、`报告交付自检` 这类报告自检项只进入 `检查点自检`，不得计入目标 skill 明细通过率。

## 报告自检与纠偏

写出 Excel 或 Markdown 后，必须逐项核对检查点全集：

- 每个适用检查点是否能在报告明细、覆盖矩阵、摘要、风险或后续动作中找到对应记录
- 所有目标 skill 派生 feature 是否至少有一条明细测试点
- `未执行`、`阻塞`、`不适用` 是否都有原因
- 报告自检项是否没有进入目标 skill 明细页通过率统计
- Excel 是否存在 `检查点自检` 页签

偏差处理：

- 目标 skill 派生 feature 缺失：在明细页补测试点；有动态证据写 `通过`/`不通过`，无动态证据写 `未执行`
- 固定方法论检查点缺失：属于目标 skill 验收内容的补到明细页；TARGET/READ/VERDICT/REPORT 自检类只写入 `检查点自检`
- TARGET/READ/VERDICT 出现在明细页：移至 `检查点自检`，删除明细页该行并重算汇总
- 结果不一致：以明细页为准重算 `<skill-name>汇总` 和 `汇总`
- 覆盖位置为空或泛化：写明具体页签与行号，例如 `<skill-name>!B12`，或明确 `未覆盖`
- 缺少原因：补真实原因，不能用 `后续再测`、`时间不足`、`环境不便`
- 证据不足但结论过高：降级业务能力结论、平台集成结论或发布建议

最多允许 3 轮纠偏。3 轮后仍未闭环时，报告状态标记为 `阻塞` 或 `不通过`，不得宣称报告合格。

## Markdown 报告门禁

仅当用户要求 Markdown 报告时适用：

- 必须使用 `assets/enterprise-acceptance-report-template.md` 的章节结构
- 必须保留模板表格字段；`9.1`、`9.2`、`9.3`、`9.4` 不得缩水成摘要表
- `9.1` 包含功能名、分类、来源证据、必要参数/前置条件、验证方式建议
- `9.2` 包含关联用例/动作、覆盖方式、当前状态、证据来源、说明
- `9.3` 包含验证层、输入/命令摘要、预期、实际、结论、证据
- `9.4` 拆分 Prompt、Script/API、Pytest、static-only、pending、blocked、skipped、out-of-scope 计数
- 必须包含 `10.4 结论一致性自检` 和 `10.4.1 结论矛盾校验`
- `9.2` 与 `9.3a` 必须一致；API 映射为 `untested/pending/blocked/dry-run` 的 action，不得在覆盖矩阵标记为 `covered`
- `READ` 功能未执行时写真实参数/数据缺口或 pending，不得写写操作风险
- 具体判定规则以 `references/report-compliance-rules.md` 为准
- 写完后必须运行 `scripts/validate_report.py`
- 校验失败时，Markdown 报告无效；先修正报告或降级结论，再重新运行校验并回填最后一次结果

## 结论门禁

- 目标从未明确确认时，不得输出 `通过` 或 `适合发布`
- 没有真实验收执行证据时，不得输出 `通过` 或 `适合发布`
- 证据不完整时，优先给出 `有条件通过`、`不通过`、`pending` 或 `blocked`
- 请求不完整时，先追问缺失目标，不输出发布结论
- Excel 报告最终结论不得高于本文件定义的结论门禁；Markdown 报告最终结论还不得高于 `references/report-compliance-rules.md` 计算出的最高结论
- 任一门禁触发降级时，必须在报告的 `10.4 结论一致性自检` 或 Excel 对应说明中写出触发项和降级原因
