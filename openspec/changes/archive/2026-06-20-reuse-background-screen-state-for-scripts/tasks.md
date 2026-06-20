## 1. Application 行为

- [x] 1.1 增加 application 内部 helper，返回运行中的非 `未知` 后台探测状态。
- [x] 1.2 更新本地 `ScreenStateReader`，优先使用可用后台状态，否则即时探测。
- [x] 1.3 复用后台状态时写入脚本运行日志。

## 2. 测试和规格

- [x] 2.1 增加 application 测试，覆盖后台状态可用时不触发即时探测。
- [x] 2.2 增加 application 测试，覆盖未知状态或未运行时回退即时探测。
- [x] 2.3 运行相关测试、全量测试、`git diff --check` 和 OpenSpec 校验。
- [x] 2.4 合并主规格并归档 change。
