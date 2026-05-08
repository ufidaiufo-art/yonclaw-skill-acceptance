# 输出质量自检清单

在输出最终验收结论之前，必须逐项完成以下自检。任何一项不通过时，不得输出 `通过` 或 `适合 YonClaw 内部发布`。

## 自检表格

| # | 自检项 | 通过标准 |
|---|--------|----------|
| Q1 | 目标确认完整性 | 阶段1的5项确认记录无空字段 |
| Q2 | 静态检查覆盖率 | 阶段2a-2e每子阶段均有结果记录，无遗漏检查项 |
| Q3 | 证据可追溯性 | 每条检查结果都引用了具体文件路径、行号或命令输出，无纯主观判断 |
| Q4 | 平台集成证据 | `yonclaw refresh/list/info` 三条命令的真实输出已记录 |
| Q5 | 动态用例完整性 | Positive/Negative/Incomplete/Safety 四类用例均有结果，未执行的有阻塞原因 |
| Q6 | 覆盖矩阵闭合性 | 功能清单中所有 feature id 在覆盖矩阵中出现，无遗漏 |
| Q7 | 结论与证据一致 | 无证据支撑的 `通过` 判定，无 `pending`/`blocked` 项被隐式升级 |
| Q8 | 交付物完整性 | Excel 已生成且格式有效（4页签含检查点自检）；Markdown（如有要求）已通过校验 |
| Q9 | 敏感能力可审计 | 敏感能力清单显式产出，零敏感项也写了 `无敏感能力` |
| Q10 | 结论门禁合规 | Excel 结论不高于 `report-generation-rules.md` 允许的上限；Markdown 结论还不高于 `report-compliance-rules.md` 允许的上限 |
| Q11 | 阶段产物完整 | `skill-info.json`、`checkpoints-covered.json`、`test-results.json` 三文件已写出且通过 `validate_checkpoints.mjs` 或 `validate_checkpoints.py` |
| Q12 | 检查点自检闭合 | `检查点自检` 页签每行覆盖位置指向具体页签!单元格或明确写 `未覆盖`，无泛化表述 |

## 输出要求

自检结果必须在验收报告的收尾部分呈现，格式为：`自检项 | 结果(通过/不通过) | 说明`。
