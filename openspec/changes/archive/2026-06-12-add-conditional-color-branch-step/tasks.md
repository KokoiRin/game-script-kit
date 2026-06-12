## 1. 领域模型

- [x] 1.1 新增 `src/game_automation/domain/conditions.py`，定义 `ColorIs` 和 `Condition`，校验颜色容差范围
- [x] 1.2 修改 `src/game_automation/domain/actions.py`，新增 `If` 控制流步骤并把它纳入 `Step`
- [x] 1.3 修改 `src/game_automation/domain/__init__.py`，导出 `ColorIs`、`Condition` 和 `If`
- [x] 1.4 更新 `tests/test_script_model.py`，覆盖颜色条件、非法容差、`If` 校验、空 else 和嵌套控制流

## 2. Runner 条件解释

- [x] 2.1 修改 `src/game_automation/engine/runner.py`，注入可选 `PixelColorReader` 并支持 `If`
- [x] 2.2 在 runner 中实现 `ColorIs` 评估，使用脚本窗口解析条件点并按每通道容差比较颜色
- [x] 2.3 更新 `tests/test_runner.py`，覆盖 then/else、空 else、窗口解析、容差、缺少 color reader 报错和嵌套控制流

## 3. Adapter 与 CLI 组装

- [x] 3.1 修改 `src/game_automation/adapters/dry_run.py`，新增固定颜色 dry-run reader
- [x] 3.2 修改 `src/game_automation/star_cli.py`，为 dry-run 增加 `--dry-run-color` 参数并注入固定颜色 reader
- [x] 3.3 修改 `src/game_automation/star_cli.py`，真实运行时注入桌面取色 adapter 并报告 setup 错误
- [x] 3.4 更新 `tests/test_dry_run.py` 和 `tests/test_script_cli.py`，覆盖 dry-run 颜色参数、默认颜色、真实运行 adapter 注入和 setup 错误

## 4. 示例脚本与脚本管理

- [x] 4.1 新增 `src/game_automation/scripts_manager/conditional_color_demo.py`，定义可验证 then/else 的条件分支示例脚本
- [x] 4.2 修改 `src/game_automation/scripts_manager/__init__.py` 和 `catalog.py`，把示例脚本注册进默认 catalog
- [x] 4.3 更新 `tests/test_script_catalog.py` 和 CLI transcript 测试，覆盖示例脚本可列出且 dry-run 两条分支都可运行

## 5. 验证

- [x] 5.1 运行 `openspec validate add-conditional-color-branch-step --strict`
- [x] 5.2 运行 `.venv/bin/python -m pytest`
- [x] 5.3 运行 `git diff --check`

## 6. 边界修正

- [x] 6.1 新增 `src/game_automation/engine/script_requirements.py`，把脚本端口需求分析从 CLI 移到 engine
- [x] 6.2 新增 `src/game_automation/engine/condition_evaluator.py`，把条件评估和运行时端口缺失校验从 runner 移到独立模块
- [x] 6.3 修改 `src/game_automation/star_cli.py` 和 `runner.py`，让 CLI 不直接依赖脚本 AST 细节，runner 不承载完整条件判断逻辑
- [x] 6.4 新增脚本需求分析和条件评估测试，并重跑 OpenSpec、pytest 和 diff 检查
