# 使用 Python 函数编写任务

在工作区的 `scripts/` 中创建 `.py` 文件。文件中的 `TASK` 字面量声明名称、目标窗口和资源，`run(ctx)` 执行流程。Python 的函数、分支、循环、返回值和异常处理可以直接使用。

## 创建并模拟运行

下面的任务包含一个辅助函数和三次点击。点位相对任务声明的原生窗口；dry-run 不打开窗口，按写下的窗口相对坐标执行替身。

```python
"""演示使用命名点位组合一个有限任务。"""

TASK = {
    "name": "我的任务",
    "resources": {"points": {"按钮": {"x": 100, "y": 200}}},
}


def click_once(ctx):
    """执行一轮操作。"""
    ctx.click("按钮")
    ctx.wait(0.5)


def run(ctx):
    """在十秒有效任务时间内完成三轮操作。"""
    with ctx.deadline(10):
        for _ in range(3):
            click_once(ctx)
```

保存到 `<workspace>/scripts/my_task.py`，再执行以下命令。

```bash
.venv/bin/star --workspace /absolute/path/to/workspace list
.venv/bin/star --workspace /absolute/path/to/workspace details 我的任务
.venv/bin/star --workspace /absolute/path/to/workspace run 我的任务 --dry-run
```

原生应用的运行页使用相同目录和任务名称。修改文件后点击“重新加载”。发现和详情读取只解析源码与字面量，启动任务时才执行模块及入口。一次运行使用发现时保存的主文件源码快照。

## 声明目标与资源

`TASK` 支持 `name`、`target`、`resources`、`requires`。`target` 和 `resources` 使用下面的字面量结构。图片文件相对所选工作区的 `assets/`。

任务发现会检查声明字段。`resources` 只接受 `points`、`images`、`regions` 和 `searches`；点位、区域和搜索对象中的未知字段会报告资源名称与字段位置。修正文件后在原生运行页点击“重新加载”，即可更新任务列表与诊断。

```python
TASK = {
    "name": "等待任务入口",
    "target": {
        "application": "Example",
        "window_title": "Example window",
        "width": 856,
        "height": 674,
        "backend": "macos-window-background",
    },
    "resources": {
        "images": {"入口图片": "entry.png"},
        "searches": {
            "入口": {"image": "入口图片", "min_confidence": 0.94},
        },
    },
    "requires": {"states": ["主页"]},
}
```

本地声明的点位、图片与搜索自动参与依赖检查。状态与共享搜索只来自 `assets/window-states.json`；使用共享搜索时，在 `requires.searches` 中列出名称。`requires` 的 `points`、`images`、`searches`、`states` 接受名称列表，`colors` 接受布尔值。状态依赖和 `colors` 决定是否装配状态读取与取色能力。

真实运行必须声明完整 `target`，`target.backend` 只能是 `macos-window` 或 `macos-window-background`，不接受命令行选窗或屏幕绝对坐标。省略 `target` 的任务仍可 dry-run，无需打开窗口。

任务元信息必须是 Python 字面量，入口是接收一个位置参数的同步普通函数。名称重复和格式错误按文件报告。以下划线开头的文件可保存辅助代码，任务通过相对导入复用，例如 `from ._helpers import open_panel`。辅助模块在本次运行中加载，各次运行使用独立模块命名空间。

## 使用动作和观察接口

作者可从 `game_automation.task` 导入 `TaskContext`、`TaskTimeout` 和 `TargetNotFound`。

| 接口 | 行为 |
| --- | --- |
| `ctx.find(name)` | 查询命名搜索或图片，返回 `ImageMatch` 或 `None` |
| `ctx.click(point)` | 点击命名点位或 `Point` |
| `ctx.click_image(name, timeout=8)` | 等待目标，发送前重新定位并点击 |
| `ctx.wait_image(name, timeout=8, interval=0.5)` | 等待图片并返回命中结果 |
| `ctx.state()` | 读取当前界面状态 |
| `ctx.wait_state(name, timeout=8)` | 等待界面状态 |
| `ctx.wait_for(query, timeout=8, interval=0.5)` | 轮询函数，返回其第一个真值结果 |
| `ctx.color(point)` | 读取命名点位或 `Point` 的颜色 |
| `ctx.drag(start, end, duration=0)` | 在窗口内拖拽 |
| `ctx.hotkey("command", "v")` | 执行组合键 |
| `ctx.wait(seconds)` | 使用可取消的运行时等待 |
| `ctx.check_cancelled()` | 检查用户停止请求及当前期限 |
| `with ctx.deadline(seconds)` | 给一段流程设置有效任务时间上限 |
| `with ctx.scope(checkpoint=check)` | 在动作与等待边界调用检查函数，可抛出任务自己的退出信号 |

图片操作优先解析同名搜索，其次解析图片。需要偏移点击时传入 `offset=Point(x, y)`。`wait_image`、`wait_state` 的 `timeout=None` 表示持续等待到满足或取消。

`find`、`wait_image` 和 `click_image` 可显式指定 `min_confidence`。点击前重新定位也使用同一阈值。需要点击后连续发送组合键时，可用 `ctx.click(..., then_hotkeys=(("command", "v"), ("enter",)))` 或 `ctx.click_image(..., then_hotkeys=...)`。

## 处理局部失败

等待到期抛出 `TaskTimeout`。直接点击时找不到必需图片抛出 `TargetNotFound`。函数可以只处理当前一段，再重新观察画面选择下一步。

```python
from game_automation.task import TaskTimeout


def enter_panel(ctx):
    """等待入口，超时后检查是否已经到达目标页面。"""
    try:
        ctx.wait_image("入口", timeout=8)
    except TaskTimeout:
        return ctx.state() == "目标页面"
    ctx.click_image("入口")
    ctx.wait_state("目标页面", timeout=8)
    return True
```

输入已经发出后，恢复逻辑先确认当前画面，再决定下一步。任务函数共享同一次窗口会话、任务时钟和输入提交边界。平台暂停期间扣除暂停时间，已经提交的输入继续由平台完成清理。

期限在上下文调用及等待轮询时检查，嵌套期限服从最早到期的一层。到期抛 `TaskTimeout`，其 `scope_id` 指明实际到期作用域。作用域事件使用独立身份，已经成功的动作保留自己的结果。纯计算循环的期限需要作者主动调用上下文检查或有限循环。

预算耗尽后正常结束一段流程时，只处理本层期限，嵌套使用时让外层期限继续传播。

```python
from game_automation.task import TaskTimeout


def poll_for_five_minutes(ctx):
    """在五分钟预算内检测按钮，耗尽本层预算后返回。"""
    scope_id = None
    try:
        with ctx.deadline(300) as scope_id:
            while True:
                if ctx.find("使用按钮"):
                    ctx.click_image("使用按钮")
                ctx.wait(0.5)
    except TaskTimeout as exc:
        if scope_id is None or exc.scope_id != scope_id:
            raise
```

任务需要在长等待中响应画面变化时，可将退出检查函数放入 `ctx.scope(checkpoint=...)`。检查函数自行抛出任务定义的异常，所属流程捕获后继续，普通 Python 循环仍由任务代码组织。

## 理解停止和验证范围

用户停止会穿过普通的 `except Exception` 恢复逻辑。后台在任务目录内的 Python 代码执行期间检查取消，覆盖模块顶层和纯 Python 循环。线程 tracing 在任务退出时恢复，平台输入和清理使用自身的取消边界。第三方阻塞调用需要等待返回，原生宿主保留已有后台超时回收机制。

正常返回使用 `completed`，未捕获等待超时使用 `timed_out`，未捕获的必需图片缺失使用 `stopped_unmet_condition`。这些结果描述执行情况，业务完成仍需目标应用中的证据。

函数任务的详情展示声明资源与入口文件，实际分支通过运行日志展示。dry-run 执行真实 Python 流程，设备与识图使用替身。固定模拟画面能覆盖的分支有限，场景变化应通过 fake 验证，再进行必要的实机验收。
