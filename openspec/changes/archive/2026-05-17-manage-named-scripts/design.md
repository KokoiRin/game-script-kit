## Context

当前脚本散落在两个位置：

- `src/game_automation/core/demo_workflow.py`：保存 `DEMO_SCRIPT`，并通过 `run_demo_workflow()` 直接执行。
- `src/game_automation/core/recorded_click_script.py`：保存 `RECORDED_CLICK_SCRIPT`，并通过独立 `game-recorded-clicks` CLI 执行。

`Script` 当前只有 `window` 和 `actions`，没有稳定名称。CLI 如果继续为每个脚本新增一个入口，脚本数量一多就会让 `pyproject.toml`、README 和测试同步膨胀。这个变更要把脚本定义集中到独立目录，并提供一个按名称查询和执行脚本的统一边界。

## Goals / Non-Goals

**Goals:**
- `Script` 记录稳定 `name`，用于展示、查找和 CLI 启动。
- 新增一个脚本定义目录，用户编辑某个脚本时能直接找到对应文件。
- 新增 `ScriptCatalog`，统一提供脚本列表、按名称读取、重复名称校验和未知名称错误。
- 新增通用 CLI：`game-scripts list` 和 `game-scripts run <name>`。
- 复用现有 `ScriptRunner`、`InputDevice`、dry-run 设备和 macOS adapter，不改变动作执行语义。

**Non-Goals:**
- 不新增 YAML/JSON 脚本格式。
- 不做图形化编辑器。
- 不做脚本参数化、循环、条件、图像识别或 OCR。
- 不移除现有 demo CLI；`game-recorded-clicks` 是否保留兼容入口在实现中只做轻量适配，不再作为新增脚本的主要入口。

## Proposed File Layout

新增和调整后的文件结构如下：

```text
src/game_automation/
├── core/
│   ├── script.py                 # Script 增加 name 字段和校验
│   ├── script_catalog.py          # 新增：ScriptCatalog / ScriptNotFoundError
│   ├── demo_workflow.py           # 调整：从 scripts.demo 读取 demo 脚本或保留兼容构造函数
│   └── recorded_click_script.py   # 调整：薄兼容层，委托到 scripts.recorded_clicks
├── scripts/
│   ├── __init__.py                # 新增：导出 DEFAULT_SCRIPT_CATALOG
│   ├── demo.py                    # 新增：DEMO_SCRIPT = Script(name="demo", ...)
│   ├── recorded_clicks.py         # 新增：RECORDED_CLICKS_SCRIPT = Script(name="recorded-clicks", ...)
│   └── catalog.py                 # 新增：组装 DEFAULT_SCRIPT_CATALOG
└── script_cli.py                  # 新增：game-scripts CLI

tests/
├── test_script_catalog.py         # 新增：catalog 列表/读取/重复/未知名称
├── test_script_cli.py             # 新增：list/run dry-run/未知名称
├── test_script_model.py           # 调整：name 字段与校验
└── test_recorded_click_script.py  # 调整：确认兼容层仍返回命名脚本
```

## Runtime Architecture

第一版采用“Python 脚本定义 + 显式注册表”的结构：

```text
scripts/demo.py ─┐
                 ├─> scripts/catalog.py ─> DEFAULT_SCRIPT_CATALOG
scripts/recorded_clicks.py ┘                      │
                                                   ▼
script_cli.py ── get/list ──> ScriptCatalog ──> ScriptRunner ──> InputDevice
```

关键边界：

- `scripts/*.py` 只负责定义 `Script` 对象，不直接创建 adapter，也不直接执行。
- `ScriptCatalog` 只负责管理脚本集合，不知道 CLI 参数，也不知道 macOS adapter。
- `script_cli.py` 负责解析命令、选择 dry-run 或 macOS device、打印 dry-run 操作。
- `ScriptRunner` 继续只负责把 `Script.actions` 转成 `InputDevice` 调用。

## Data Model

`Script` 改为：

```python
@dataclass(frozen=True, slots=True)
class Script:
    name: str
    window: Window
    actions: tuple[Action, ...]
```

校验规则：

- `actions` 不能为空，保留现有错误语义。
- `name.strip()` 不能为空，否则抛出 `ValueError("script name cannot be empty")`。
- 不在 `Script` 内强制 kebab-case。原因是领域模型只负责“有名称”，命令行友好格式作为 README 推荐和脚本定义约定；重复名称由 `ScriptCatalog` 统一处理。

## Script Catalog API

新增 `src/game_automation/core/script_catalog.py`：

```python
class ScriptNotFoundError(LookupError):
    pass

@dataclass(frozen=True, slots=True)
class ScriptCatalog:
    scripts: tuple[Script, ...]

    def __post_init__(self) -> None:
        # 校验重复名称

    def list_names(self) -> tuple[str, ...]:
        # 返回按名称排序或注册顺序固定的名称

    def get(self, name: str) -> Script:
        # 找不到时抛出 ScriptNotFoundError
```

实现选择：

- 内部在 `__post_init__` 构建 `dict[str, Script]` 会和 frozen dataclass 有冲突；第一版可以直接使用私有 `_by_name` 并通过 `object.__setattr__` 设置，或者不用 dataclass、手写 `__init__`。
- 为了实现简单，推荐手写 `__init__(self, scripts: Iterable[Script])`，内部保存 `tuple` 和 `dict`。
- `list_names()` 返回 `tuple(self._by_name)`，保持注册顺序，方便 README 示例和测试稳定。

错误信息：

- 重复名称：`ValueError("duplicate script name: <name>")`
- 未知名称：`ScriptNotFoundError("unknown script: <name>")`

## Script Definition Modules

新增 `src/game_automation/scripts/demo.py`：

- 移入当前 `DEMO_SCRIPT` 的动作序列。
- 设置 `name="demo"`。
- 提供 `build_demo_script() -> Script`，返回该常量。

新增 `src/game_automation/scripts/recorded_clicks.py`：

- 移入当前 `RECORDED_CLICK_SCRIPT` 的动作序列。
- 设置 `name="recorded-clicks"`。
- 提供 `build_recorded_clicks_script() -> Script`，返回该常量。

新增 `src/game_automation/scripts/catalog.py`：

```python
DEFAULT_SCRIPT_CATALOG = ScriptCatalog(
    (
        build_demo_script(),
        build_recorded_clicks_script(),
    )
)
```

后续用户新增脚本时，只需要：

1. 在 `src/game_automation/scripts/<script_name>.py` 新增脚本定义。
2. 在 `scripts/catalog.py` 注册到 `DEFAULT_SCRIPT_CATALOG`。
3. 运行 `game-scripts list` 确认可见。

## CLI Design

新增 `src/game_automation/script_cli.py`，并在 `pyproject.toml` 添加：

```toml
game-scripts = "game_automation.script_cli:main"
```

命令形态：

```bash
game-scripts list
game-scripts run demo --dry-run
game-scripts run recorded-clicks --dry-run
game-scripts run recorded-clicks
```

参数规则：

- `list`：逐行打印脚本名称。
- `run <name>`：默认真实执行 macOS adapter。
- `run <name> --dry-run`：只打印计划操作，不移动真实鼠标。
- `run <name> --macos`：保留兼容参数，语义等同于默认运行。
- `--dry-run` 和 `--macos` 互斥。
- 未知脚本名称返回 `1`，向 stderr 打印 `unknown script: <name>`。

dry-run 复用现有 `DryRunInputDevice` 和 `RecordedOperation`：

- 可以继续从 `game_automation.cli` import，减少重复实现。
- 如果后续发现 `cli.py` 依赖方向不清晰，再把 dry-run device 抽到 `adapters/desktop/dry_run.py`；本变更第一版不做额外抽取。

## Compatibility Plan

- `core/demo_workflow.py` 保留 `build_demo_script()` 和 `run_demo_workflow()`，内部改为从 `game_automation.scripts.demo` 取脚本。
- `core/recorded_click_script.py` 保留 `build_recorded_click_script()` 和 `run_recorded_click_script()`，内部委托到 `scripts.recorded_clicks`，避免已有测试和旧 CLI 立即失效。
- `recorded_click_cli.py` 可以继续存在，但实现上应复用 `DEFAULT_SCRIPT_CATALOG.get("recorded-clicks")` 或 `build_recorded_click_script()`。
- README 把 `game-scripts` 作为推荐入口，旧 `game-recorded-clicks` 可以标记为兼容入口。

## Test Plan

新增/调整测试：

- `tests/test_script_model.py`
  - `Script(name="demo", ...)` 保留名称。
  - 空名称和纯空白名称被拒绝。
  - 现有空动作测试继续通过。
- `tests/test_script_catalog.py`
  - catalog 返回注册脚本名称。
  - catalog 按名称返回同一个 `Script`。
  - 未知名称抛出 `ScriptNotFoundError`。
  - 重复名称抛出 `ValueError`。
- `tests/test_script_cli.py`
  - `main(["list"])` 输出 `demo` 和 `recorded-clicks`。
  - `main(["run", "recorded-clicks", "--dry-run"])` 输出等待和点击。
  - `main(["run", "recorded-clicks"])` 默认加载 macOS adapter。
  - `main(["run", "missing", "--dry-run"])` 返回 `1` 并向 stderr 输出未知脚本。
- 现有 `tests/test_recorded_click_cli.py` 和 `tests/test_demo_workflow.py` 继续通过，证明兼容入口没有被破坏。

## Risks / Trade-offs

- [Risk] Python 脚本定义对非开发者不如 YAML/JSON 友好 -> 先用当前领域对象直接表达脚本，后续可以在 `ScriptCatalog` 后面增加文件解析。
- [Risk] 用户新增脚本后忘记注册 -> README 明确新增脚本的两步流程；后续如脚本数量增加，再考虑自动发现。
- [Risk] dry-run device 从 `cli.py` import 让 `script_cli.py` 依赖 demo CLI 模块 -> 第一版接受这个轻量复用；如果 CLI 共享代码继续增加，再抽出 `testing` 或 `adapters/dry_run` 模块。
- [Risk] 旧 `game-recorded-clicks` 和新 `game-scripts run recorded-clicks` 功能重复 -> README 以新入口为主，旧入口只保持兼容。
