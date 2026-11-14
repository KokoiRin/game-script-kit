"""为入口测试建立直接 Python 函数任务及显式资源声明。

本模块只包装源码和元信息，不解释动作，也不执行任务。
运行行为由公开 run_task 和 TaskContext 入口验证。
"""

from dataclasses import replace
from pathlib import Path
from textwrap import indent

from game_automation.portable.domain import NamedImage, TargetCatalog
from game_automation.portable.domain.task import FunctionTask, TaskRequirements
from game_automation.portable.domain.windows import UnboundWindow


def function_task(
    name, body, *, window=None, resources=None, requires=None, target=None, templates=()
):
    """将普通 Python 函数体与测试明确声明的资源绑定为任务。"""
    resources = resources or TargetCatalog()
    resources = replace(
        resources,
        images=resources.images
        + tuple(
            NamedImage(f"inline-{index}", template)
            for index, template in enumerate(templates)
        ),
    )
    requires = requires or TaskRequirements()
    requires = replace(
        requires,
        points=tuple(
            dict.fromkeys(
                requires.points + tuple(item.name for item in resources.points)
            )
        ),
        images=tuple(
            dict.fromkeys(
                requires.images + tuple(item.name for item in resources.images)
            )
        ),
        searches=tuple(
            dict.fromkeys(
                requires.searches + tuple(item.name for item in resources.searches)
            )
        ),
    )
    source = (
        "from game_automation.portable.domain import *\n"
        "from game_automation.task import TaskTimeout, TargetNotFound\n\n"
        "def run(ctx):\n"
        '    """执行本例直接 Python 流程。"""\n' + indent(body, "    ") + "\n"
    )
    return FunctionTask(
        name,
        Path(__file__).with_name("task.py"),
        source,
        window=window or UnboundWindow(),
        resources=resources,
        target=target,
        requires=requires,
    )
