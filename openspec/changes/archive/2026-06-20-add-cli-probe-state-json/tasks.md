## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 规格，定义 `probe-state --json` 的行为和字段。
- [x] 1.2 添加 CLI 行为测试，覆盖成功 JSON 输出和候选状态映射。

## 2. 实现

- [x] 2.1 为 `probe-state` 增加 `--json` 参数。
- [x] 2.2 将 `ScreenStateProbeResult` 转换为稳定 JSON payload。
- [x] 2.3 保持默认文本输出、错误码和 stderr 行为不变。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
