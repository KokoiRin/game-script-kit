## 1. 领域模型

- [x] 1.1 用 TDD 增加 `Point.offset`。
- [x] 1.2 用 TDD 增加 `OffsetTarget` 和 `PointRef.offset`。
- [x] 1.3 扩展 `ClickTarget`，让偏移目标成为合法点击目标。

## 2. 执行语义

- [x] 2.1 用 TDD 让 runner 解析固定点位 offset。
- [x] 2.2 用 TDD 让 runner 解析命名点位 offset。
- [x] 2.3 补充图片 anchor + offset 执行测试，确认既有 offset 在 anchor 后应用。

## 3. 验证

- [x] 3.1 运行相关单测和完整 `.venv/bin/python -m pytest`。
- [x] 3.2 运行 `openspec validate add-target-offsets --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 运行 `git diff --check` 并检查没有平台依赖进入 portable 核心。
