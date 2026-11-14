"""执行已校验的 Python 任务源码并管理本次运行的模块与取消检查。

本模块不创建平台能力或运行会话。任务通过注入的上下文执行动作，应用层
负责关闭运行时。线程局部 tracing 只检查任务目录中的 Python 代码。
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING
from uuid import uuid4

from game_automation.portable.domain.task import FunctionTask
from game_automation.portable.engine.cancellation import RunCancelled
from game_automation.portable.engine.ports import CancellationToken

if TYPE_CHECKING:
    from game_automation.portable.engine.task_context import TaskContext


def run_function_task(
    task: FunctionTask,
    context: TaskContext,
    *,
    cancellation_token: CancellationToken | None = None,
) -> None:
    """在独立模块命名空间执行源码快照和同步入口，结束时恢复当前线程。"""
    package_name = f"_star_task_{uuid4().hex}"
    module_name = f"{package_name}.task"
    package = ModuleType(package_name)
    package.__path__ = [str(task.source_path.parent)]
    module = ModuleType(module_name)
    module.__file__ = str(task.source_path)
    module.__package__ = package_name
    previous_trace = sys.gettrace()
    task_directory = task.source_path.parent.resolve()
    task_files: dict[str, bool] = {str(task.source_path): True}

    def check_cancelled() -> None:
        """用终止信号传播用户取消，让任务中的普通异常捕获继续有效。"""
        if cancellation_token is not None and cancellation_token.is_cancelled():
            raise RunCancelled("script run cancelled")

    def trace_task(frame, event, arg):
        """只在任务 Python 帧检查终止取消，避免打断平台提交与清理。"""
        filename = frame.f_code.co_filename
        if filename not in task_files:
            task_files[filename] = not filename.startswith("<") and Path(
                filename
            ).resolve().is_relative_to(task_directory)
        if not task_files[filename]:
            return None
        if event == "call":
            frame.f_trace_opcodes = True
        check_cancelled()
        return trace_task

    sys.modules[package_name] = package
    sys.modules[module_name] = module
    try:
        check_cancelled()
        if cancellation_token is not None:
            sys.settrace(trace_task)
        exec(
            compile(task.source, str(task.source_path), "exec", dont_inherit=True),
            module.__dict__,
        )
        entrypoint = module.__dict__.get("run")
        if (
            not callable(entrypoint)
            or inspect.iscoroutinefunction(entrypoint)
            or inspect.isgeneratorfunction(entrypoint)
            or inspect.isasyncgenfunction(entrypoint)
        ):
            raise ValueError("task must define a synchronous run(ctx)")
        returned = entrypoint(context)
        if (
            inspect.isawaitable(returned)
            or inspect.isgenerator(returned)
            or inspect.isasyncgen(returned)
        ):
            if inspect.iscoroutine(returned) or inspect.isgenerator(returned):
                returned.close()
            raise ValueError("task run(ctx) must complete synchronously")
        check_cancelled()
    except KeyboardInterrupt as exc:
        raise RunCancelled("script run cancelled") from exc
    except SystemExit as exc:
        raise RuntimeError(f"task exited with code {exc.code}") from exc
    finally:
        sys.settrace(previous_trace)
        for name in tuple(sys.modules):
            if name == package_name or name.startswith(f"{package_name}."):
                sys.modules.pop(name, None)
