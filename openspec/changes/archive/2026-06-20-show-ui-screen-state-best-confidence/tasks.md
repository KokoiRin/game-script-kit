## 1. 规格与测试

- [x] 1.1 补充 `local-control-ui` 规格，定义 UI 候选展示最佳置信度。
- [x] 1.2 添加 application/UI HTTP 测试，覆盖候选摘要和 JSON payload 的 `best_confidence`。
- [x] 1.3 添加前端静态资源测试，覆盖候选列表渲染最佳置信度。

## 2. 实现

- [x] 2.1 扩展 `ScreenStateProbeCandidateSummary` 并从领域候选复制 `best_confidence`。
- [x] 2.2 让 `/api/screen-state-probe` 输出候选 `best_confidence`。
- [x] 2.3 让前端界面探测候选列表展示最佳置信度。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
