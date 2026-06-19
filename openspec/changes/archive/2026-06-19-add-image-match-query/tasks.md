## 1. 查询模型

- [x] 1.1 用 TDD 增加 `ImageLookupResult`，覆盖 found、match、rect、center、confidence。
- [x] 1.2 用 TDD 增加 `locate_image` 查询函数，覆盖直接模板、命名图片和未找到结果。

## 2. 执行语义接入

- [x] 2.1 让条件评估通过 `locate_image` 判断图片存在。
- [x] 2.2 让 runner 图片目标点击通过 `locate_image` 获取匹配结果。

## 3. 验证

- [x] 3.1 运行相关单测和完整 `.venv/bin/python -m pytest`。
- [x] 3.2 运行 `openspec validate add-image-match-query --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 运行 `git diff --check` 并检查没有平台依赖进入 portable 核心。
