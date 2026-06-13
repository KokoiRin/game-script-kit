## 1. 领域模型

- [x] 1.1 修改 `src/game_automation/domain/actions.py`，新增 `WaitUntil` 并纳入 `Step`
- [x] 1.2 修改 `src/game_automation/domain/__init__.py`，导出 `WaitUntil`
- [x] 1.3 更新 `tests/test_script_model.py`，覆盖 `WaitUntil` 字段保留、非法 timeout、非法 interval 和嵌套控制流

## 2. Runner 与端口需求

- [x] 2.1 修改 `src/game_automation/engine/runner.py`，支持执行 `WaitUntil`
- [x] 2.2 保持条件评估委托给 `condition_evaluator`，通过 `InputDevice.wait()` 推进轮询并在超时时抛 `TimeoutError`
- [x] 2.3 修改 `src/game_automation/engine/script_requirements.py`，递归识别 `WaitUntil` 中的颜色条件端口需求
- [x] 2.4 更新 `tests/test_runner.py` 和 `tests/test_script_requirements.py`，覆盖立即满足、等待后满足、超时、剩余 timeout 预算和嵌套控制流

## 3. 示例脚本与 CLI 验证

- [x] 3.1 新增 `src/game_automation/scripts_manager/wait_until_color_demo.py`，定义条件等待示例脚本
- [x] 3.2 修改 `src/game_automation/scripts_manager/__init__.py` 和 `catalog.py`，注册示例脚本
- [x] 3.3 修改 `src/game_automation/star_cli.py`，将 `TimeoutError` 映射为非零退出码和清晰 stderr
- [x] 3.4 更新 `tests/test_script_catalog.py` 和 `tests/test_script_cli.py`，覆盖列表、dry-run 成功路径和 dry-run 超时路径

## 4. 文档与验证

- [x] 4.1 更新 `README.md`，补充 `WaitUntil(ColorIs)` 能力和端到端 dry-run 验证命令
- [x] 4.2 运行 `openspec validate add-wait-until-color-step --strict`
- [x] 4.3 运行 `.venv/bin/python -m pytest`
- [x] 4.4 运行 `git diff --check`
