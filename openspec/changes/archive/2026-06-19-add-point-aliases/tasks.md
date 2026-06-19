## 1. 领域模型

- [x] 1.1 用 TDD 增加 `NamedPoint`、`PointRef`、`TargetCatalog` 和未知点位错误。
- [x] 1.2 扩展 `Script`，让脚本可以携带默认空资源目录且保持现有构造兼容。
- [x] 1.3 扩展 `ClickTarget`，让 `Click(PointRef(...))` 成为合法领域模型。

## 2. 执行语义

- [x] 2.1 用 TDD 接入 runner 命名点位点击解析，覆盖 `ScreenWindow` 和 `AreaWindow`。
- [x] 2.2 补充未知点位运行错误，错误信息包含点位名称。

## 3. 验证

- [x] 3.1 运行相关单测和完整 `.venv/bin/python -m pytest`。
- [x] 3.2 运行 `openspec validate add-point-aliases --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 运行 `git diff --check` 并检查没有平台依赖进入 portable 核心。
