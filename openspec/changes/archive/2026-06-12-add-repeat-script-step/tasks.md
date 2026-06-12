## 1. 领域模型整理

- [x] 1.1 修改 `tests/test_script_model.py`，新增 `Script.steps`、`Repeat(times, steps)`、非法 `times`、空 `Repeat.steps` 和嵌套 Repeat 的模型测试
- [x] 1.2 修改 `src/game_automation/domain/actions.py`，新增 `Repeat`，定义 `PrimitiveAction` 和 `Step` 类型别名，并校验 `Repeat.times > 0`、`Repeat.steps` 非空
- [x] 1.3 修改 `src/game_automation/domain/script.py`，将 `Script.actions` 改为 `Script.steps`，并把空脚本错误改为脚本至少需要一个步骤
- [x] 1.4 修改 `src/game_automation/domain/__init__.py`，导出 `Repeat`、`PrimitiveAction` 和 `Step`
- [x] 1.5 运行 `.venv/bin/python -m pytest tests/test_script_model.py -v` 验证领域模型

## 2. Runner 执行树

- [x] 2.1 修改 `tests/test_runner.py`，覆盖 `Repeat(times=3)` 展开执行顺序
- [x] 2.2 修改 `tests/test_runner.py`，覆盖嵌套 `Repeat` 的递归执行顺序和窗口坐标解析
- [x] 2.3 修改 `src/game_automation/engine/runner.py`，将单层 action 循环改为递归 `_run_steps(script, steps)`，并支持 `Repeat`
- [x] 2.4 保持未知步骤类型抛出清晰 `TypeError`
- [x] 2.5 运行 `.venv/bin/python -m pytest tests/test_runner.py -v` 验证 runner 行为

## 3. 脚本定义和文档迁移

- [x] 3.1 修改 `src/game_automation/scripts_manager/demo.py` 和 `recorded_clicks.py`，将 `actions=(...)` 迁移为 `steps=(...)`
- [x] 3.2 修改 `tests/test_script_catalog.py`、`tests/test_script_cli.py` 和其他受影响测试中的 `Script(..., actions=...)`
- [x] 3.3 更新 `README.md`，将脚本示例、项目结构说明和新增脚本说明从 actions 术语迁移为 steps，并补充 `Repeat(times, steps)` 示例
- [x] 3.4 使用 `rg "actions|Action"` 检查是否存在需要迁移的旧术语；保留确实表示原子动作的说明

## 4. 回归验证

- [x] 4.1 运行 `.venv/bin/python -m pytest`，确认全部测试通过
- [x] 4.2 运行 `.venv/bin/star list`，确认命名脚本目录未受影响
- [x] 4.3 运行 `.venv/bin/star run demo --dry-run`，确认 dry-run 输出仍按预期顺序打印
- [x] 4.4 运行 `openspec validate add-repeat-script-step`，确认变更规格仍有效
- [x] 4.5 运行 `git diff --check`，确认没有空白问题
