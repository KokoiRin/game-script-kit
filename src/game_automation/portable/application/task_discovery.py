"""统一任务目录发现、源码读取和逐文件诊断。

本模块拥有目录与编码边界，将同一次读取的源码交给 Python 解析器。
它不执行任务、不判断资源是否就绪，也不创建平台能力。
"""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.domain.task import FunctionTask


@dataclass(frozen=True, slots=True)
class TaskLoadError:
    """保存可以逐文件展示的发现诊断。"""

    file: str
    message: str


@dataclass(frozen=True, slots=True)
class TaskFileEntry:
    """将任务定义与目录中的来源文件绑定。"""

    file: str
    script: FunctionTask


@dataclass(frozen=True, slots=True)
class TaskDiscoveryResult:
    """同时保留有效任务与被隔离的文件错误。"""

    entries: tuple[TaskFileEntry, ...] = ()
    errors: tuple[TaskLoadError, ...] = ()


def discover_task_files(
    script_dir: Path,
    *,
    asset_root: Path,
) -> TaskDiscoveryResult:
    """按稳定文件顺序解析 Python 任务，逐文件隔离读取和语法错误。"""
    from game_automation.portable.application.function_task_loader import (
        parse_function_task_source,
    )

    try:
        paths = tuple(script_dir.iterdir())
    except FileNotFoundError:
        return TaskDiscoveryResult()
    except NotADirectoryError:
        error = TaskLoadError(
            script_dir.name, f"script path is not a directory: {script_dir}"
        )
        return TaskDiscoveryResult(errors=(error,))
    except OSError as exc:
        error = TaskLoadError(script_dir.name, f"{script_dir.name}: {exc}")
        return TaskDiscoveryResult(errors=(error,))
    entries: list[TaskFileEntry] = []
    errors: list[TaskLoadError] = []
    for path in sorted(paths, key=lambda item: item.name):
        if path.suffix == ".json":
            errors.append(
                TaskLoadError(
                    path.name,
                    f"{path.name}: JSON task format is unsupported; migrate to Python TASK and run(ctx)",
                )
            )
            continue
        if path.suffix != ".py":
            continue
        if path.suffix == ".py" and path.name.startswith("_"):
            continue
        try:
            source = _read_source(path)
            task = parse_function_task_source(
                source, path=path.resolve(), asset_root=asset_root
            )
            if task is not None:
                entries.append(TaskFileEntry(path.name, task))
        except (
            OSError,
            UnicodeError,
            SyntaxError,
            LookupError,
            TypeError,
            ValueError,
        ) as exc:
            errors.append(TaskLoadError(path.name, f"{path.name}: {exc}"))
    return TaskDiscoveryResult(tuple(entries), tuple(errors))


def _read_source(path: Path) -> str:
    """从单次字节快照读取文本，Python 源码遵守编码声明。"""
    data = path.read_bytes()
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    with io.TextIOWrapper(io.BytesIO(data), encoding=encoding) as stream:
        return stream.read()
