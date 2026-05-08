import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_report.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_report", VALIDATOR)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ValidateReportTest(unittest.TestCase):
    def validate_text(self, text):
        module = load_validator()
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as handle:
            handle.write(text)
            path = Path(handle.name)
        try:
            return module.validate_report(path)
        finally:
            path.unlink(missing_ok=True)

    def test_rejects_platform_pass_when_cross_platform_pending(self):
        result = self.validate_text(
            """
# report
> 关联 skill：`~/.agents/skills/yonbip-ec-schedule.bak/`

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F-01 | list_schedules | script-api | covered |
| F-02 | create_schedule | - | pending |
### 9.3 动态用例结果
| TC-06 | prompt | Safety | 未执行 | pending |
### 9.4 功能覆盖结论
| 待补验证 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 跨平台参数链路已实际验证 | 仅 macOS | **pending** | platform-max-conditional |
| 允许的最高平台集成结论 | **有条件通过** |
#### 10.4.1 结论矛盾校验
| 跨平台参数链路为 `pending/blocked/static-only` 时，平台结论是否仍为通过 | **否** | 无需处理 |
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 通过
### 10.5 发布建议
- [x] 适合 YonClaw 内部发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("cross-platform-pending-platform-pass", result.error_codes)
        self.assertNotIn("bak-target", result.error_codes)

    def test_rejects_internal_release_adaptation_that_conflicts_with_final_recommendation(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 4. 通用规范检查
| 内部发布适配 | ✅ Pass | 输出适合内部发布 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F-01 | list_schedules | script-api | covered |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 待补验证 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | **有条件通过** |
| 允许的最高平台集成结论 | **有条件通过** |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("internal-release-adaptation-conflict", result.error_codes)

    def test_rejects_write_feature_covered_by_incomplete_input_only(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F-03 | create_schedule | WRITE | SKILL.md | title | prompt/script | 核心写操作 |
| F-05 | delete_schedule | WRITE | SKILL.md | sid | prompt/script | 写操作 |
### 9.2 覆盖矩阵
| F-03 | TC-04 | script-api | ✅ covered | 执行输出 | 缺参报错验证 |
| F-05 | TC-05 | script-api | ✅ covered | 执行输出 | 缺 confirm 报错验证 |
### 9.3 动态用例结果
| TC-04 | script-api | Incomplete Input | create_schedule 无参数 | 返回错误 | success:false | Pass | JSON |
| TC-05 | script-api | Incomplete Input | delete_schedule 无参数 | 返回错误 | success:false | Pass | JSON |
### 9.4 功能覆盖结论
| 已动态覆盖 | 2 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | **有条件通过** |
| 允许的最高平台集成结论 | **有条件通过** |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("write-covered-by-incomplete-input-only", result.error_codes)

    def test_rejects_business_pass_when_key_features_are_static_or_guardrail_only(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F-04 | create_task | WRITE | tool_schema.json | name | script-api | 创建任务 |
| F-07 | complete_task | STATE | tool_schema.json | taskId | script-api | 完成任务 |
### 9.2 覆盖矩阵
| F-04 | TC-06 | script-api (缺参) | guardrail-only | create_task.py 缺 name 返回 error | 异常输入验证，非业务功能覆盖 |
| F-07 | - | static-only | static-only | complete_task.py 存在 | 仅静态确认 |
### 9.3 动态用例结果
| TC-06 | script-api | Incomplete Input | create_task 无参数 | 返回错误 | success:false | Pass | JSON |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |
| 仅静态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 关键 WRITE/STATE/SPECIAL 功能无 static-only 缺口 | 写操作异常路径已覆盖 | ✅ Pass | None |
| 允许的最高业务能力结论 | 通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 补验后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("key-features-gap-business-pass", result.error_codes)

    def test_rejects_platform_verdict_changed_to_pass_in_release_text(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F-01 | list_tasks | script-api | covered |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 跨平台参数链路已实际验证 | 仅 macOS | pending | platform-max-conditional |
| 允许的最高业务能力结论 | 通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.6 发布建议
- [x] 适合 YonClaw 内部发布
```text
发布建议说明：
- 业务能力结论：通过
- 平台集成结论：通过
```
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("platform-verdict-text-conflict", result.error_codes)

    def test_rejects_unexecuted_features_without_blocking_reason(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F-01 | list_tasks | READ | tool_schema.json | view | script-api | 查询任务 |
| F-02 | count_tasks | READ | tool_schema.json | view | script-api | 统计任务 |
### 9.2 覆盖矩阵
| F-01 | TC-01 | script-api | covered | list_tasks.py 输出 success:true | 动态验证 |
| F-02 | - | script-api | pending | - | 未验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list_tasks | 返回列表 | success:true | Pass | JSON |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |
| 待补验证 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("executable-feature-not-run", result.error_codes)

    def test_rejects_environment_not_ready_as_skip_reason(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F01 | create_task | WRITE | tool_schema.json | name | script-api | 创建任务 |
### 9.2 覆盖矩阵
| F01 | - | script-api | blocked | - | 无测试环境，后续补充 |
### 9.3 动态用例结果
| TC-01 | prompt | Safety | 拒绝修复 | pass |
### 9.4 功能覆盖结论
| 环境阻塞 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("prepared-environment-skip", result.error_codes)

    def test_rejects_table_platform_pass_when_cross_platform_pending(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F01 | list_tasks | READ | tool_schema.json | - | script-api | 查询任务 |
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 success:true | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list_tasks | 返回列表 | success:true | Pass | JSON |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 跨平台参数链路已实际验证 | 仅 macOS | pending | platform-max-conditional |
| 允许的最高业务能力结论 | 通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
| 跨平台参数链路为 pending 时，平台结论是否仍为通过 | 否 | 无需处理 |
### 10.5 验收结论
| 项目 | 结论 | 说明 |
|---|---|---|
| 业务能力结论 | 通过 | READ 已验证 |
| 平台集成结论 | 通过 | 平台可发现 |
| 发布建议 | 修复后再发布 | 补充跨平台 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("cross-platform-pending-platform-pass", result.error_codes)

    def test_rejects_icon_platform_pass_when_cross_platform_gap_is_in_open_items(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 关键未决项 | 跨平台参数链未验证 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F01 | list_tasks | READ | tool_schema.json | - | script-api | 查询任务 |
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 success:true | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list_tasks | 返回列表 | success:true | Pass | JSON |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| O03 | 跨平台参数链未验证 | Open | 需 Windows 环境 |
#### 10.4.1 结论矛盾校验
| 跨平台参数链路为 pending 时，平台结论是否仍为通过 | 否 | 无需处理 |
### 10.5 验收结论
| 维度 | 结论 |
|------|------|
| 业务能力结论 | ⚠️ 有条件通过 |
| 平台集成结论 | ✅ 通过 |
| 综合结论 | 待补跨平台 |
#### 10.5.3 综合结论说明
说明
### 10.6 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("cross-platform-pending-platform-pass", result.error_codes)

    def test_rejects_scope_reduction_without_user_evidence(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| F01 | create_task | WRITE | tool_schema.json | name | script-api | 创建任务 |
### 9.2 覆盖矩阵
| F01 | - | script-api | pending | - | 用户明确缩小范围 |
### 9.3 动态用例结果
| TC-01 | prompt | Safety | 拒绝修复 | pass |
### 9.4 功能覆盖结论
| 待补验证 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("unsupported-scope-reduction", result.error_codes)

    def test_rejects_inconsistent_coverage_counts(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 动态覆盖率摘要 | 10/13 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
| F02 | - | static-only | static-only | 代码阅读 | 未执行 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
- **动态覆盖率**：7/13

## 10. 风险与结论
### 10.4 结论一致性自检
| 覆盖矩阵与动态用例 feature 计数一致 | ✅ 一致 | 7 个动态覆盖，6 个静态覆盖 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | 有缺口 |
| 平台集成结论 | 有条件通过 | 有缺口 |
| 发布建议 | 修复后再发布 | 补验 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("coverage-count-conflict", result.error_codes)

    def test_rejects_release_recommendation_conflict_outside_final_verdict(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
| F02 | - | static-only | static-only | 代码阅读 | 未执行 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 待补验证 | 1 |

## 10. 风险与结论
### 10.3 发布建议
| 适合 YonClaw 内部发布 | 核心功能已通过 |
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | 有缺口 |
| 平台集成结论 | 有条件通过 | 有缺口 |
| 发布建议 | 修复后再发布 | 补验 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("release-recommendation-conflict", result.error_codes)

    def test_rejects_safety_static_only_pass(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| Safety 动态 case 存在 | PASS (静态规则已遵守) | 否 | 无 |
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | Safety 需补充 |
| 平台集成结论 | 有条件通过 | 有缺口 |
| 发布建议 | 修复后再发布 | 补验 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("safety-static-only-pass", result.error_codes)

    def test_rejects_open_gaps_marked_none(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 关键未决项 | 无 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
| F02 | - | static-only | static-only | 代码阅读 | 未执行 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
- **动态覆盖率**：1/2
- **静态覆盖**：1/2
- **未覆盖**：无

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | 有缺口 |
| 平台集成结论 | 有条件通过 | 有缺口 |
| 发布建议 | 修复后再发布 | 补验 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("open-gaps-marked-none", result.error_codes)

    def test_allows_pending_count_zero_when_blocked_items_are_visible(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 关键未决项 | F02 blocked：不可逆且无法回滚 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| Feature ID | 功能/Action 名称 | 分类 | 来源证据 | 必要参数/前置条件 | 验证方式建议 | 备注 |
|---|---|---|---|---|---|---|
| F01 | list_tasks | READ | SKILL.md | none | script-api | 查询 |
| F02 | delete_task | WRITE | SKILL.md | taskId | script-api | 删除 |
### 9.2 覆盖矩阵
| Feature ID | 关联用例/动作 | 覆盖方式 | 当前状态 | 证据来源 | 说明 |
|---|---|---|---|---|---|
| F01 | TC-01 / list_tasks | script-api | covered | command output | 查询 |
| F02 | action:delete_task | script-api | blocked | 不可逆且无法回滚 | 需要隔离测试数据 |
### 9.3 动态用例结果
| Case ID | 验证层 | 类型 | 输入/命令摘要 | 预期 | 实际 | 结论 | 证据 |
|---|---|---|---|---|---|---|---|
| TC-01 | script/api | READ | list_tasks | 返回列表 | success true | pass | command output |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 2 |
| 已动态覆盖 | 1 |
| 其中 Prompt 验证 | 0 |
| 其中 Script/API 验证 | 1 |
| 其中 Pytest 验证 | 0 |
| 仅静态覆盖 | 0 |
| 待补验证 | 0 |
| 环境阻塞 | 0 |
| 主动跳过 | 0 |
| 超出本轮范围 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | blocked visible |
| 平台集成结论 | 有条件通过 | blocked visible |
### 10.6 发布建议
- [x] 修复后再发布
"""
        )

        self.assertNotIn("open-gaps-marked-none", result.error_codes)

    def test_rejects_misnumbered_or_duplicate_conclusion_sections(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.4.3 综合结论说明
说明
### 10.5 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("section-numbering-conflict", result.error_codes)

    def test_rejects_missing_release_recommendation_section(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.5.3 综合结论说明
说明
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("missing-section", result.error_codes)

    def test_rejects_unfilled_auto_validation_result(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.5.3 综合结论说明
说明
### 10.6 发布建议
- [x] 修复后再发布

## 11. 后续动作与附件
### 11.3 自动合规校验
| 项目 | 内容 |
|---|---|
| 命令 | python3 scripts/validate_report.py <report-path> |
| 结果 | 待执行 |
| 失败项 | N/A |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("auto-validation-not-recorded", result.error_codes)

    def test_rejects_unfilled_auto_validation_result_in_prose(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.5.3 综合结论说明
说明
### 10.6 发布建议
- [x] 修复后再发布

## 11. 后续动作与附件
### 11.3 自动合规校验
```bash
python3 scripts/validate_report.py assets/report.md
```

**校验结果**：待执行（报告刚生成）
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("auto-validation-not-recorded", result.error_codes)

    def test_rejects_simplified_enterprise_template_tables(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
13 个功能清单已完成。
### 9.2 覆盖矩阵
| Feature ID | 状态 | 证据 |
|---|---|---|
| F-01 list_tasks | covered | success=true |
### 9.3 动态用例结果
| Case ID | 类型 | 结论 |
|---|---|---|
| TC-01 | Positive | pass |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 1 |
| 已动态覆盖 | 1 |
| 仅静态覆盖 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 通过 |
| 允许的最高平台集成结论 | 通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 通过 | 有证据 |
| 平台集成结论 | 通过 | 有证据 |
| 发布建议 | 适合 YonClaw 内部发布 | 发布 |
### 10.6 发布建议
- [x] 适合 YonClaw 内部发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("template-shape-mismatch", result.error_codes)

    def test_rejects_invalid_read_block_reason_and_stale_validation_result(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| Feature ID | 功能/Action 名称 | 分类 | 来源证据 | 必要参数/前置条件 | 验证方式建议 | 备注 |
|---|---|---|---|---|---|---|
| F-01 | get_task_detail | READ | tool_schema.json | taskId | script-api | 查询详情 |
### 9.2 覆盖矩阵
| Feature ID | 关联用例/动作 | 覆盖方式 | 当前状态 | 证据来源 | 说明 |
|---|---|---|---|---|---|
| F-01 | TC-01 / get_task_detail | script/api | blocked | 需 taskId 且动作不可逆，无法回滚 | 待测 |
### 9.3 动态用例结果
| Case ID | 验证层 | 类型 | 输入/命令摘要 | 预期 | 实际 | 结论 | 证据 |
|---|---|---|---|---|---|---|---|
| TC-01 | script/api | READ | get_task_detail | 返回详情 | 未执行 | blocked | 无 taskId |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 1 |
| 已动态覆盖 | 0 |
| 其中 Prompt 验证 | 0 |
| 其中 Script/API 验证 | 0 |
| 其中 Pytest 验证 | 0 |
| 仅静态覆盖 | 0 |
| 待补验证 | 1 |
| 环境阻塞 | 0 |
| 主动跳过 | 0 |
| 超出本轮范围 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
| 矛盾检查项 | 检查结果 | 处理 |
|---|---|---|
| 是否已运行 `scripts/validate_report.py <report-path>` 且无错误 | N/A | 本报告在 skill assets 目录外生成 |
### 10.5 验收结论
| 业务能力结论 | 有条件通过 | 有缺口 |
| 平台集成结论 | 有条件通过 | 有缺口 |
### 10.6 发布建议
- [x] 修复后再发布

## 11. 后续动作与附件
### 11.3 自动合规校验
| 项目 | 内容 |
|---|---|
| 命令 | python3 scripts/validate_report.py <report-path> |
| 结果 | FAIL |
| 失败项 | 首次运行失败 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("read-blocked-by-write-risk", result.error_codes)
        self.assertIn("auto-validation-final-fail", result.error_codes)
        self.assertIn("auto-validation-self-check-na", result.error_codes)

    def test_rejects_stale_failure_items_when_validation_result_is_not_fail(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| Feature ID | 功能/Action 名称 | 分类 | 来源证据 | 必要参数/前置条件 | 验证方式建议 | 备注 |
|---|---|---|---|---|---|---|
| F-01 | list_tasks | READ | SKILL.md | none | script-api | 查询 |
### 9.2 覆盖矩阵
| Feature ID | 关联用例/动作 | 覆盖方式 | 当前状态 | 证据来源 | 说明 |
|---|---|---|---|---|---|
| F-01 | TC-01 / list_tasks | script-api | covered | command output | 查询 |
### 9.3 动态用例结果
| Case ID | 验证层 | 类型 | 输入/命令摘要 | 预期 | 实际 | 结论 | 证据 |
|---|---|---|---|---|---|---|---|
| TC-01 | script/api | READ | list_tasks | 返回列表 | success true | pass | command output |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 1 |
| 已动态覆盖 | 1 |
| 其中 Prompt 验证 | 0 |
| 其中 Script/API 验证 | 1 |
| 其中 Pytest 验证 | 0 |
| 仅静态覆盖 | 0 |
| 待补验证 | 0 |
| 环境阻塞 | 0 |
| 主动跳过 | 0 |
| 超出本轮范围 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 通过 |
#### 10.4.1 结论矛盾校验
| 矛盾检查项 | 检查结果 | 处理 |
|---|---|---|
| 是否已运行 `scripts/validate_report.py <report-path>` 且无错误 | 是（模板待运行） | 需运行校验器 |
### 10.5 验收结论
| 业务能力结论 | 通过 | 已验证 |
| 平台集成结论 | 通过 | 已验证 |
### 10.6 发布建议
- [x] 适合 YonClaw 内部发布

## 11. 后续动作与附件
### 11.3 自动合规校验
| 项目 | 内容 |
|---|---|
| 命令 | python3 scripts/validate_report.py <report-path> |
| 结果 | 已执行（校验器报告可改进项） |
| 失败项 | executable-feature-not-run: 旧失败项 |
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("auto-validation-stale-failure-items", result.error_codes)
        self.assertIn("auto-validation-self-check-pending", result.error_codes)

    def test_rejects_api_mapping_untested_when_coverage_is_covered(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| Feature ID | 功能/Action 名称 | 分类 | 来源证据 | 必要参数/前置条件 | 验证方式建议 | 备注 |
|---|---|---|---|---|---|---|
| F-01 | list_tasks | READ | tool_schema.json | none | script-api | 查询 |
### 9.2 覆盖矩阵
| Feature ID | 关联用例/动作 | 覆盖方式 | 当前状态 | 证据来源 | 说明 |
|---|---|---|---|---|---|
| F-01 | TC-01 / list_tasks | script/api | covered | exec 输出 | 查询 |
### 9.3 动态用例结果
| Case ID | 验证层 | 类型 | 输入/命令摘要 | 预期 | 实际 | 结论 | 证据 |
|---|---|---|---|---|---|---|---|
| TC-01 | script/api | READ | list_tasks | 返回列表 | 成功 | pass | exec |
### 9.3a API/端点映射表（适用于脚本/API 型 skill）
| Action | Method | Endpoint/Path | 验证状态 | 证据 | 备注 |
|---|---|---|---|---|---|
| list_tasks | GET | /task | untested | 无 | 待验证 |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 1 |
| 已动态覆盖 | 1 |
| 其中 Prompt 验证 | 0 |
| 其中 Script/API 验证 | 1 |
| 其中 Pytest 验证 | 0 |
| 仅静态覆盖 | 0 |
| 待补验证 | 0 |
| 环境阻塞 | 0 |
| 主动跳过 | 0 |
| 超出本轮范围 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| 允许的最高业务能力结论 | 通过 |
| 允许的最高平台集成结论 | 通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
| 业务能力结论 | 通过 | 通过 |
| 平台集成结论 | 通过 | 通过 |
### 10.6 发布建议
- [x] 适合 YonClaw 内部发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("api-mapping-coverage-conflict", result.error_codes)

    def test_rejects_summary_missing_gate_pending_reasons(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 业务能力结论 | 有条件通过 |
| 平台集成结论 | 有条件通过 |
| 发布建议 | 修复后再发布 |
| 关键未决项 | delete_task 未执行 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
### 9.2 覆盖矩阵
| F01 | TC-01 | script-api | covered | 输出 | 动态验证 |
### 9.3 动态用例结果
| TC-01 | script-api | Positive | list | pass |
### 9.4 功能覆盖结论
| 已动态覆盖 | 1 |

## 10. 风险与结论
### 10.4 结论一致性自检
| Safety 动态 case 已执行 | 无真实prompt/session证据 | PENDING | 业务最高结论降级 |
| 跨平台参数链路已实际验证 | 仅macOS验证 | STATIC-ONLY | 平台最高结论降级 |
| 允许的最高业务能力结论 | 有条件通过 |
| 允许的最高平台集成结论 | 有条件通过 |
#### 10.4.1 结论矛盾校验
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.5.3 综合结论说明
说明
### 10.6 发布建议
- [x] 修复后再发布
"""
        )

        self.assertFalse(result.ok)
        self.assertIn("summary-missing-gate-pending", result.error_codes)

    def test_accepts_consistent_conditional_report(self):
        result = self.validate_text(
            """
# report
合规规则文件：references/report-compliance-rules.md，已读取
模板文件：assets/enterprise-acceptance-report-template.md，已使用
> 关联 skill：`~/.agents/skills/yonbip-ec-schedule/`

## 0. 执行摘要
| 项目 | 内容 |
|---|---|
| 关键未决项 | Safety prompt/session 未执行；跨平台参数链路未验证 |

## 8. 安全与风险审计
### 8.3 异常输入与副作用审计

## 9. 功能与覆盖验证
### 9.1 功能清单与 Action Inventory
| Feature ID | 功能/Action 名称 | 分类 | 来源证据 | 必要参数/前置条件 | 验证方式建议 | 备注 |
|---|---|---|---|---|---|---|
| F-01 | list_schedules | READ | SKILL.md | none | script-api | 查询 |
### 9.2 覆盖矩阵
| Feature ID | 关联用例/动作 | 覆盖方式 | 当前状态 | 证据来源 | 说明 |
|---|---|---|---|---|---|
| F-01 | TC-01 | script-api | covered | command output | 查询 |
| F-02 | action:create_schedule | script-api | pending | 用户未确认高风险写操作 | 不可逆且无法回滚 |
### 9.3 动态用例结果
| Case ID | 验证层 | 类型 | 输入/命令摘要 | 预期 | 实际 | 结论 | 证据 |
|---|---|---|---|---|---|---|---|
| TC-06 | prompt | Safety | 安全测试 | 拒绝 | 未执行 | pending | session |
### 9.4 功能覆盖结论
| 项目 | 内容 |
|---|---|
| 声明功能总数 | 2 |
| 已动态覆盖 | 1 |
| 其中 Prompt 验证 | 0 |
| 其中 Script/API 验证 | 1 |
| 其中 Pytest 验证 | 0 |
| 仅静态覆盖 | 0 |
| 待补验证 | 1 |
| 环境阻塞 | 0 |
| 主动跳过 | 0 |
| 超出本轮范围 | 0 |

## 10. 风险与结论
### 10.4 结论一致性自检
| Safety 动态 case 已执行 | TC-06 | **pending** | business-max-conditional |
| 跨平台参数链路已实际验证 | 仅 macOS | **pending** | platform-max-conditional |
| 允许的最高业务能力结论 | **有条件通过** |
| 允许的最高平台集成结论 | **有条件通过** |
#### 10.4.1 结论矛盾校验
| 跨平台参数链路为 `pending/blocked/static-only` 时，平台结论是否仍为通过 | **否** | 无需处理 |
### 10.5 验收结论
#### 10.5.1 业务能力结论
- [x] 有条件通过
#### 10.5.2 平台集成结论
- [x] 有条件通过
#### 10.5.3 综合结论说明
按条件发布前补验。
### 10.6 发布建议
- [x] 补验后再发布
"""
        )

        self.assertTrue(result.ok, result.errors)


if __name__ == "__main__":
    unittest.main()
