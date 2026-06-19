## 1. 领域模型

- [x] 1.1 用 TDD 增加 `ImageMatch.point_at(anchor)` 和 `ImageLookupResult.point_at(anchor)`。
- [x] 1.2 用 TDD 扩展 `ImageTarget.anchor`，覆盖默认值和非法 anchor。

## 2. 执行语义

- [x] 2.1 用 TDD 让 runner 图片目标点击使用 anchor 点位，并保持默认中心点兼容。

## 3. 验证

- [x] 3.1 运行相关单测和完整 `.venv/bin/python -m pytest`。
- [x] 3.2 运行 `openspec validate add-image-match-anchors --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 运行 `git diff --check` 并检查没有平台依赖进入 portable 核心。
