## 1. Script 模型命名

- [x] 1.1 修改 `src/game_automation/core/script.py`，为 `Script` 增加必填 `name: str` 字段
- [x] 1.2 在 `Script.__post_init__()` 中保留空动作校验，并新增空名称/纯空白名称校验
- [x] 1.3 修改 `tests/test_script_model.py`，覆盖脚本名称保留、空名称拒绝、纯空白名称拒绝
- [x] 1.4 更新所有现有 `Script(...)` 构造调用，至少包含 `demo` 和 `recorded-clicks` 两个稳定名称

## 2. 脚本定义目录

- [x] 2.1 新增 `src/game_automation/scripts/__init__.py`，作为脚本定义包入口
- [x] 2.2 新增 `src/game_automation/scripts/demo.py`，把当前 demo 动作序列迁入 `DEMO_SCRIPT = Script(name="demo", ...)`
- [x] 2.3 新增 `src/game_automation/scripts/recorded_clicks.py`，把当前 recorded click 动作序列迁入 `RECORDED_CLICKS_SCRIPT = Script(name="recorded-clicks", ...)`
- [x] 2.4 调整 `src/game_automation/core/demo_workflow.py`，让 `build_demo_script()` 从 `game_automation.scripts.demo` 返回脚本
- [x] 2.5 调整 `src/game_automation/core/recorded_click_script.py`，让 `build_recorded_click_script()` 委托到 `game_automation.scripts.recorded_clicks`

## 3. ScriptCatalog 管理边界

- [x] 3.1 新增 `src/game_automation/core/script_catalog.py`，定义 `ScriptNotFoundError` 和 `ScriptCatalog`
- [x] 3.2 实现 `ScriptCatalog.__init__(scripts)`，保存注册顺序并构建名称索引
- [x] 3.3 在 `ScriptCatalog` 初始化时检测重复 `Script.name`，重复时抛出 `ValueError("duplicate script name: <name>")`
- [x] 3.4 实现 `ScriptCatalog.list_names() -> tuple[str, ...]`，返回注册顺序下的脚本名称
- [x] 3.5 实现 `ScriptCatalog.get(name: str) -> Script`，未知名称时抛出 `ScriptNotFoundError("unknown script: <name>")`
- [x] 3.6 新增 `tests/test_script_catalog.py`，覆盖列表、按名称读取、未知名称和重复名称

## 4. 默认脚本注册表

- [x] 4.1 新增 `src/game_automation/scripts/catalog.py`，创建 `DEFAULT_SCRIPT_CATALOG`
- [x] 4.2 将 `demo` 和 `recorded-clicks` 注册到 `DEFAULT_SCRIPT_CATALOG`
- [x] 4.3 在 `src/game_automation/scripts/__init__.py` 导出 `DEFAULT_SCRIPT_CATALOG`
- [x] 4.4 在 `src/game_automation/core/__init__.py` 导出 `ScriptCatalog` 和 `ScriptNotFoundError`

## 5. 通用脚本 CLI

- [x] 5.1 新增 `src/game_automation/script_cli.py`，实现 `build_parser()` 和 `main(argv=None)`
- [x] 5.2 实现 `game-scripts list`，逐行输出 `DEFAULT_SCRIPT_CATALOG.list_names()`
- [x] 5.3 实现 `game-scripts run <name> --dry-run`，按名称读取脚本并通过 `ScriptRunner` dry-run 打印操作
- [x] 5.4 实现 `game-scripts run <name>` 默认运行时导入 `MacOSPointerDevice` 并执行脚本
- [x] 5.5 实现 `--dry-run` / `--macos` 互斥；`run` 默认使用 macOS，`--macos` 保留为兼容参数
- [x] 5.6 捕获 `ScriptNotFoundError`，向 stderr 打印错误并返回退出码 `1`
- [x] 5.7 在 `pyproject.toml` 添加 `game-scripts = "game_automation.script_cli:main"`

## 6. 兼容入口调整

- [x] 6.1 保留 `src/game_automation/recorded_click_cli.py`，内部继续支持 `--dry-run` 和 `--macos`
- [x] 6.2 让 `recorded_click_cli.py` 复用迁移后的 named script，避免保留第二份动作序列
- [x] 6.3 保留 `game-recorded-clicks` console script，README 标记为兼容入口而非推荐新增方式

## 7. CLI 测试

- [x] 7.1 新增 `tests/test_script_cli.py`，验证 `main(["list"])` 输出 `demo` 和 `recorded-clicks`
- [x] 7.2 验证 `main(["run", "recorded-clicks", "--dry-run"])` 输出等待和点击操作
- [x] 7.3 验证 `main(["run", "recorded-clicks"])` 默认使用 macOS adapter
- [x] 7.4 验证 `main(["run", "missing", "--dry-run"])` 返回 `1`，stderr 包含 `unknown script: missing`
- [x] 7.5 更新现有 `tests/test_recorded_click_cli.py`，确认旧入口仍可 dry-run

## 8. 文档与验证

- [x] 8.1 更新 README 的代码结构，新增 `scripts/`、`core/script_catalog.py` 和 `script_cli.py`
- [x] 8.2 更新 README 的运行说明，以 `game-scripts list` 和 `game-scripts run <name>` 作为推荐入口
- [x] 8.3 在 README 增加“新增/编辑脚本”的最小流程：新增 `scripts/<name>.py` 并注册到 `scripts/catalog.py`
- [x] 8.4 运行 `.venv/bin/python -m pytest`
- [x] 8.5 运行 `openspec validate manage-named-scripts`
- [x] 8.6 运行 `git diff --check`
