"""验证声明依赖驱动端口装配，不执行任务或推导 Python 控制流。

这些测试通过 FunctionTask 与公开元信息解析入口观察运行需求。
"""

from pathlib import Path

import pytest

from game_automation.portable.application.function_task_loader import (
    parse_function_task_source,
)
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from game_automation.portable.engine.runtime_requirements import (
    inspect_runtime_requirements,
)


@pytest.mark.parametrize(
    "requires, expected",
    [
        (TaskRequirements(), (False, False, False)),
        (TaskRequirements(points=("button",)), (False, False, False)),
        (TaskRequirements(colors=True), (True, False, False)),
        (TaskRequirements(images=("button",)), (False, True, False)),
        (TaskRequirements(searches=("button",)), (False, True, False)),
        (TaskRequirements(states=("home",)), (False, False, True)),
        (
            TaskRequirements(colors=True, images=("button",), states=("home",)),
            (True, True, True),
        ),
    ],
)
def test_declared_capabilities_select_runtime_ports(requires, expected):
    """端口需求仅来自显式声明，各种能力可以独立组合。"""
    task = FunctionTask(
        "ports", Path("ports.py"), "def run(ctx): pass", requires=requires
    )

    result = inspect_runtime_requirements(task)

    assert (
        result.needs_color_reader,
        result.needs_image_locator,
        result.needs_screen_state_reader,
    ) == expected


def test_local_resources_select_image_port_before_task_execution(tmp_path):
    """文件中的图片和搜索声明无需执行源码便参与运行装配。"""
    source = """TASK = {"name": "resources", "resources": {
        "images": {"button": "button.png"},
        "searches": {"confirm": {"image": "button"}}
    }}
def run(ctx):
    raise AssertionError("discovery executed the task")
"""
    task = parse_function_task_source(
        source, path=tmp_path / "task.py", asset_root=tmp_path
    )

    assert inspect_runtime_requirements(task).needs_image_locator
    assert task.requires.images == ("button",)
    assert task.requires.searches == ("confirm",)


def test_python_body_does_not_implicitly_declare_capabilities():
    """调用上下文的 Python 语句不会被静态解释为隐式依赖。"""
    task = FunctionTask("explicit", Path("explicit.py"), "def run(ctx): ctx.state()")

    assert not inspect_runtime_requirements(task).needs_screen_state_reader
