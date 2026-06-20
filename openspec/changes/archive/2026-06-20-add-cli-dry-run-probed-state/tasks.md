## 1. 规格与测试

- [x] 1.1 补充 `script-management` 规格，定义 CLI dry-run 使用当前探测状态的行为。
- [x] 1.2 添加 CLI 成功路径测试：先探测状态，再用该状态 dry-run 状态条件脚本。
- [x] 1.3 添加 CLI 错误路径测试：未启用 dry-run、状态来源冲突、探测失败。

## 2. 实现

- [x] 2.1 为 `star run` 增加 `--dry-run-probed-screen-state` 参数。
- [x] 2.2 在运行脚本前解析 dry-run 状态来源，复用 application 层单次状态探测。
- [x] 2.3 保持默认 dry-run、手工 `--dry-run-screen-state` 和真实运行行为不变。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
