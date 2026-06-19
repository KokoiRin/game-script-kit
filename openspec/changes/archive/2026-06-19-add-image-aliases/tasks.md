## 1. 领域模型

- [x] 1.1 用 TDD 增加 `NamedImage`、`ImageRef`、`TargetCatalog.resolve_image` 和未知图片错误。
- [x] 1.2 扩展 `ImageExists` 和 `ImageTarget`，允许接收 `ImageRef` 且保持 `ImageTemplate` 兼容。

## 2. 执行语义

- [x] 2.1 用 TDD 接入条件评估中的命名图片解析。
- [x] 2.2 用 TDD 接入 runner 图片目标点击中的命名图片解析。
- [x] 2.3 更新脚本需求分析，识别命名图片条件和命名图片点击目标。

## 3. 验证

- [x] 3.1 运行相关单测和完整 `.venv/bin/python -m pytest`。
- [x] 3.2 运行 `openspec validate add-image-aliases --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 运行 `git diff --check` 并检查没有平台依赖进入 portable 核心。
