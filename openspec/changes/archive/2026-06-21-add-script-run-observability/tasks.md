## 1. 结构化结束原因

- [x] 1.1 为 `ScriptRunResult` 和后台 `ScriptRunStatus` 增加结束原因。
- [x] 1.2 将取消、超时、运行失败、配置失败、setup 失败映射到稳定原因。
- [x] 1.3 在 HTTP `/api/run-script`、`/api/script-run`、`/api/stop-script` 状态 payload 中暴露结束原因。

## 2. 步骤事件日志

- [x] 2.1 新增脚本运行事件模型和格式化输出。
- [x] 2.2 runner 在步骤开始、成功、失败、点击、等待、Repeat、If、WaitUntil 处产生日志事件。
- [x] 2.3 后台 UI 会话收集结构化事件，并继续把事件写入 stdout 文本日志。

## 3. 验证和规划

- [x] 3.1 补充 runner、script_run、local_control、local UI HTTP 测试。
- [x] 3.2 运行相关测试和全量测试。
- [x] 3.3 运行 OpenSpec 校验和 `git diff --check`。
- [x] 3.4 输出网页 UI 日志展示规划。
