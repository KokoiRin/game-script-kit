## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 规格，定义候选最佳置信度诊断字段。
- [x] 1.2 添加领域/engine 测试，覆盖未命中候选保留 `best_confidence`。
- [x] 1.3 添加 CLI JSON 和文本输出测试，覆盖 `best_confidence`。

## 2. 实现

- [x] 2.1 扩展批量图像匹配和界面状态候选结果模型。
- [x] 2.2 让桌面批量图像匹配 adapter 在未命中时保留最佳分数。
- [x] 2.3 让状态探测结果和 CLI 输出暴露最佳置信度。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
