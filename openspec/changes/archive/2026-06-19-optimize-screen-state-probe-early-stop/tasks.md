## 1. 批量匹配早停

- [x] 1.1 扩展 `ImageBatchMatchResult` 表达 skipped 状态，并测试 skipped 不等同于未命中。
- [x] 1.2 为 `ScreenImageBatchLocator.locate_many` 增加 `stop_on_first_match` 参数，更新 fake 和调用方测试。
- [x] 1.3 更新 desktop adapter，实现命中即停和 skipped 结果，并测试实际匹配数量、结果顺序和日志。

## 2. 状态探测语义

- [x] 2.1 更新 `probe_screen_state` 默认启用 batch 早停，按候选顺序决定当前状态。
- [x] 2.2 更新单图 fallback，让命中后停止并把后续候选标记为 skipped。

## 3. 验证和归档

- [x] 3.1 运行聚焦测试、完整 pytest、OpenSpec strict 校验和 `git diff --check`。
- [x] 3.2 归档 OpenSpec change，按项目规则提交并 push。
