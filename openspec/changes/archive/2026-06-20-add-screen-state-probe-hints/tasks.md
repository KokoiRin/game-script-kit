## 1. 测试

- [x] 1.1 添加领域结果测试，覆盖全部已执行候选 `best_confidence=0` 时生成诊断提示。
- [x] 1.2 添加领域结果测试，覆盖普通低置信度未命中不生成截图不可用提示。
- [x] 1.3 添加 CLI 文本和 JSON 测试，覆盖 `probe-state` 输出 `hints`。
- [x] 1.4 添加 UI HTTP payload 和静态脚本测试，覆盖后台探测状态返回并展示 `hints`。

## 2. 实现

- [x] 2.1 在 `ScreenStateProbeResult` 增加结构化 `hints` 派生属性。
- [x] 2.2 在 CLI `probe-state` 文本输出和 JSON payload 中展示 `hints`。
- [x] 2.3 在后台界面探测状态中保存最近一轮 `hints`。
- [x] 2.4 在 UI HTTP payload 和前端界面探测 tab 中展示 `hints`。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 CLI smoke：`star probe-state` 和 `star probe-state --json`。
- [x] 3.3 归档 OpenSpec change。
