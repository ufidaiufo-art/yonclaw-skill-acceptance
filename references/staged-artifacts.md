# Staged Artifacts

本文件定义验收过程中的三类阶段产物。缺少任一产物，或产物未通过 `scripts/validate_checkpoints.*`，不得生成正式验收报告。

## 输出目录

默认输出到当前 workspace 的 `assets/<skill-name>-acceptance/`。用户指定目录时按用户目录写入，目录不存在时创建。

## `skill-info.json`

生成时机：完成目标确认和强制读取后。

必含字段：

- `skill`：至少包含 `name`、`path`、`version`、`description`
- `workspace`
- `mode`
- `read_files`：必须包含目标 `SKILL.md`
- `dependencies`
- `features`：每项至少包含 `id`、`name`、`category`、`source`、`dynamic_required`
- `guards`
- `write_or_state_capabilities`
- `environment`

没有 `skill-info.json`，不得生成检查点覆盖文件、动态测试文件或报告。

## `checkpoints-covered.json`

生成时机：完成检查点全集打标后。

生成规则：

- 必须以验收技能目录中的 `assets/checkpoints.json` 为固定模板
- 必须追加目标 skill 派生 feature 检查点
- 每个检查点至少包含 `id`、`category`、`checkpoint`、`status`、`coverage`、`evidence`、`reason`
- `status` 只能使用 `covered`、`failed`、`blocked`、`skipped`、`not_applicable`
- `covered` 必须有 `evidence`
- `failed`、`blocked`、`skipped`、`not_applicable` 必须有 `reason`

没有 `checkpoints-covered.json`，不得执行报告生成。

## `test-results.json`

生成时机：完成动态用例后。

生成规则：

- 必须记录 `positive`、`negative`、`incomplete_input`、`safety` 四类基线 case
- 未执行的 case 也要记录为 `blocked` 或 `skipped` 并写原因
- 每条用例至少包含 `id`、`type`、`target_feature_ids`、`input`、`command_or_session`、`expected`、`actual`、`result`、`evidence`、`side_effect_check`

没有 `test-results.json`，不得执行报告生成。

## 校验命令

优先使用 Node.js 校验：

```bash
node <yonclaw-skill-acceptance>/scripts/validate_checkpoints.mjs \
  --skill-info <output-dir>/skill-info.json \
  --checkpoints <output-dir>/checkpoints-covered.json \
  --test-results <output-dir>/test-results.json
```

如 Node.js 不可用，可使用 Python 等价校验：

```bash
python3 <yonclaw-skill-acceptance>/scripts/validate_checkpoints.py \
  --skill-info <output-dir>/skill-info.json \
  --checkpoints <output-dir>/checkpoints-covered.json \
  --test-results <output-dir>/test-results.json
```

校验失败时，必须按错误修正对应阶段产物；不能绕过校验直接生成报告。
