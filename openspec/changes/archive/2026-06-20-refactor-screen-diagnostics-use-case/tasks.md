## 1. 抽取诊断模块

- [x] 1.1 新增 `ScreenDiagnosticsUseCase`，迁移 6 个屏幕诊断用例。
- [x] 1.2 新增诊断 artifact 模块，迁移 Pillow 绘图、裁剪、黑屏检测、旧 PNG 清理和安全文件名处理。
- [x] 1.3 让 `LocalControlApplication` 保留原公开方法并委托新 use case。

## 2. 测试

- [x] 2.1 将诊断产物/诊断用例行为覆盖迁移到新 module interface。
- [x] 2.2 保留 `LocalControlApplication` facade 可见行为测试。

## 3. 验证

- [x] 3.1 运行 `tests/test_local_control.py`、`tests/test_local_control_ui.py`、`tests/test_script_cli.py`。
- [x] 3.2 运行 `.venv/bin/python -m pytest`。
- [x] 3.3 运行 `openspec validate --specs --strict` 和本 change 严格校验。
- [x] 3.4 运行 `git diff --check`。
