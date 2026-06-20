## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 和 `local-control-ui` 规格，定义候选最佳位置诊断字段。
- [x] 1.2 添加领域/engine/adapter 测试，覆盖未命中候选保留 `best_rect`。
- [x] 1.3 添加 CLI JSON/文本输出测试，覆盖 `best_rect`。
- [x] 1.4 添加 UI application/HTTP/前端测试，覆盖候选最佳位置展示。

## 2. 实现

- [x] 2.1 扩展批量图像匹配和界面状态候选结果模型。
- [x] 2.2 让桌面批量图像匹配 adapter 在未命中时保留最佳位置。
- [x] 2.3 让状态探测结果和 CLI 输出暴露最佳位置。
- [x] 2.4 让 UI 状态探测摘要、HTTP payload 和候选列表展示最佳位置。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
