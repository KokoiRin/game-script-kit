"""验证函数任务通过应用入口执行、取消及释放同一次运行会话。

任务源码使用真实 Python，设备、时钟和目标窗口由替身隔离。
这些测试不读取桌面，也不将动作执行当作游戏任务完成。
"""

import sys
from contextlib import contextmanager
from threading import Event, Thread

import pytest

from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain import (
    AreaWindow,
    NamedPoint,
    Point,
    Rect,
    ScreenWindow,
    TargetCatalog,
)
from game_automation.portable.domain.task import (
    FunctionTask,
    ScriptTarget,
    TaskRequirements,
)


def function_task(tmp_path, source, **options):
    """建立可独立导入辅助模块的任务源码快照。"""
    path = tmp_path / "scripts" / "flow.py"
    path.parent.mkdir(exist_ok=True)
    path.write_text(source)
    return FunctionTask("函数任务", path, source, **options)


class Token:
    """提供可由测试线程请求的取消信号。"""

    def __init__(self):
        """创建尚未取消的事件。"""
        self.event = Event()

    def is_cancelled(self):
        """读取当前取消请求。"""
        return self.event.is_set()


def test_function_control_flow_returns_and_relative_helpers(tmp_path, capsys):
    """函数、分支和返回值直接由 Python 执行，辅助模块按本次运行隔离。"""
    source = '''from ._helper import count

def move(ctx):
    """返回本轮需要执行的动作次数。"""
    return count()

def run(ctx):
    """按函数结果执行分支和有限循环。"""
    for number in range(move(ctx)):
        if number == 1:
            continue
        ctx.wait(0)
    return
    raise AssertionError("unreachable")
'''
    task = function_task(tmp_path, source)
    helper = task.source_path.parent / "_helper.py"
    helper.write_text('def count():\n    """返回动作次数。"""\n    return 3\n')
    modules_before = {name for name in sys.modules if name.startswith("_star_task_")}

    result = run_script(task, dry_run=True)

    assert result.finish_reason == "completed"
    assert capsys.readouterr().out.count("wait") == 2
    assert {
        name for name in sys.modules if name.startswith("_star_task_")
    } == modules_before


@pytest.mark.parametrize(
    "source, expected",
    [
        (
            'def run(ctx):\n    """模拟未处理异常。"""\n    raise RuntimeError("broken task")\n',
            "failed",
        ),
        (
            'def run(ctx):\n    """模拟未处理等待超时。"""\n    raise TimeoutError("missing view")\n',
            "timed_out",
        ),
        (
            'def run(ctx):\n    """模拟任务退出请求。"""\n    raise SystemExit(0)\n',
            "failed",
        ),
    ],
)
def test_function_failure_restores_existing_trace(tmp_path, source, expected):
    """任务失败保持原有 tracing，并归一化为可再次启动的结果。"""
    previous = sys.gettrace()
    result = run_script(
        function_task(tmp_path, source), dry_run=True, cancellation_token=Token()
    )

    assert result.finish_reason == expected
    assert result.exit_code == 1
    assert sys.gettrace() is previous


def test_keyboard_interrupt_finishes_as_cancelled(tmp_path):
    """任务的键盘中断归一化为取消，运行会话可以记录明确终态。"""
    task = function_task(
        tmp_path,
        'def run(ctx):\n    """模拟终端中断。"""\n    raise KeyboardInterrupt\n',
    )

    result = run_script(task, dry_run=True)

    assert (result.exit_code, result.finish_reason) == (130, "cancelled")


def test_function_source_keeps_its_own_python_annotation_semantics(tmp_path):
    """执行源码只使用任务声明的 future 特性，避免继承框架编译选项。"""
    task = function_task(
        tmp_path,
        "def helper(value: int):\n"
        '    """保留普通 Python 注解求值行为。"""\n'
        "    pass\n"
        "\n"
        "def run(ctx):\n"
        '    """检查包装执行保持独立源码的注解语义。"""\n'
        '    assert helper.__annotations__["value"] is int\n',
    )

    result = run_script(task, dry_run=True)

    assert result.finish_reason == "completed"


@pytest.mark.parametrize(
    "source",
    [
        'def run(ctx):\n    """进入单行计算循环。"""\n    while True: pass\n',
        'while True: pass\n\ndef run(ctx):\n    """顶层执行被取消后不会调用。"""\n    pass\n',
        'def run(ctx):\n    """普通异常恢复不能吞掉用户取消。"""\n    try:\n        while True: pass\n    except Exception:\n        while True: pass\n',
        '''from game_automation.task import TaskTimeout

def run(ctx):
    """局部超时恢复后仍可停止纯 Python 循环。"""
    try:
        with ctx.deadline(0.01):
            ctx.wait(1)
    except TaskTimeout:
        pass
    while True: pass
''',
    ],
)
def test_user_stop_cancels_python_without_action_calls(tmp_path, source):
    """用户停止覆盖模块顶层、普通异常处理及局部恢复后的计算循环。"""
    token = Token()
    results = []
    task = function_task(tmp_path, source)

    def execute():
        """在与应用相同的后台线程中运行任务。"""
        results.append(run_script(task, dry_run=True, cancellation_token=token))

    worker = Thread(target=execute, daemon=True)
    worker.start()
    token.event.wait(0.05)
    token.event.set()
    worker.join(2)

    assert not worker.is_alive()
    assert results[0].finish_reason == "cancelled"
    assert results[0].exit_code == 130


def test_native_function_helpers_share_one_runtime_and_window(tmp_path):
    """多个任务函数共用一个原生会话，并在成功或失败时释放一次。"""

    class Device:
        """记录已发送的绝对坐标。"""

        def __init__(self):
            """初始化动作记录。"""
            self.clicks = []

        def click(self, target):
            """记录一个原子点击。"""
            self.clicks.append(target)

    class Factory:
        """为整份任务提供一个窗口及唯一设备。"""

        def __init__(self):
            """初始化会话计数和设备。"""
            self.opened = 0
            self.closed = 0
            self.device = Device()

        @contextmanager
        def open(self, target, requirements, cancellation, logger):
            """模拟窗口运行时的开启和最终清理。"""
            self.opened += 1
            try:
                yield RuntimePorts(AreaWindow(Rect(100, 200, 400, 300)), self.device)
            finally:
                self.closed += 1

    task = function_task(
        tmp_path,
        "def click_once(ctx):\n"
        '    """点击本次绑定窗口中的命名点位。"""\n'
        '    ctx.click("button")\n'
        "\n"
        "def run(ctx):\n"
        '    """组合多个函数并共用窗口会话。"""\n'
        "    for _ in range(2):\n"
        "        click_once(ctx)\n",
        target=ScriptTarget("Fake", "Fake window", 400, 300, "macos-window-background"),
        resources=TargetCatalog(points=(NamedPoint("button", Point(10, 20)),)),
        requires=TaskRequirements(points=("button",)),
    )
    factory = Factory()

    result = run_script(task, dry_run=False, real_runtime_factory=factory)

    assert result.finish_reason == "completed"
    assert (factory.opened, factory.closed) == (1, 1)
    assert factory.device.clicks == [Point(110, 220), Point(110, 220)]


def test_execution_and_cleanup_failures_are_both_reported(tmp_path):
    """执行与资源关闭同时失败时，最终结果保留两个实际错误。"""

    class FailingCleanupFactory:
        """提供可以启动但最终关闭失败的运行会话。"""

        @contextmanager
        def open(self, target, requirements, cancellation, logger):
            """模拟源码执行后窗口流关闭失败。"""
            try:
                yield RuntimePorts(ScreenWindow(), object())
            finally:
                raise RuntimeError("stream shutdown failed")

    task = function_task(
        tmp_path,
        "def run(ctx):\n"
        '    """模拟任务执行失败。"""\n'
        '    raise RuntimeError("business input failed")\n',
        target=ScriptTarget("Fake", "Fake window", 400, 300, "macos-window-background"),
    )

    result = run_script(
        task, dry_run=False, real_runtime_factory=FailingCleanupFactory()
    )

    assert result.finish_reason == "cleanup_failed"
    assert "business input failed" in result.error_message
    assert "stream shutdown failed" in result.error_message
