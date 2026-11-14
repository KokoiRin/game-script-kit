"""提供 Python 任务作者使用的稳定动作上下文和可恢复异常。

本模块集中导出任务创作所需接口，不发现任务、不创建平台端口或启动运行。
应用层在执行 run(ctx) 时注入 TaskContext，任务使用普通 Python 控制流。
"""

from game_automation.portable.domain.geometry import Point
from game_automation.portable.engine.cancellation import RunCancelled
from game_automation.portable.engine.task_context import (
    TargetNotFound,
    TaskContext,
    TaskTimeout,
)

__all__ = ["Point", "TaskContext", "TaskTimeout", "TargetNotFound", "RunCancelled"]
