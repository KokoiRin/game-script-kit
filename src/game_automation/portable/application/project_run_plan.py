"""读取工作区保存的任务顺序与任务后等待配置。

本模块校验任务引用配置；任务发现、运行端口和后台生命周期由相邻用例管理。
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.run_plan import validate_plan_wait


@dataclass(frozen=True)
class SavedPlanEntry:
    """记录一个已保存的任务引用与结束后等待。"""

    name: str
    wait_after_seconds: float = 0


@dataclass(frozen=True)
class SavedRunPlan:
    """保存工作区的一套有序任务流程。"""

    name: str
    entries: tuple[SavedPlanEntry, ...]


def load_saved_run_plan(workspace: Path) -> SavedRunPlan | None:
    """读取可选流程配置并在任何任务执行前校验全部条目。"""
    path = workspace / ".star" / "run-plan.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc
    return parse_saved_run_plan(data)


def parse_saved_run_plan(data: object) -> SavedRunPlan:
    """校验完整流程，保留条目顺序与重复任务。"""
    if not isinstance(data, dict) or set(data) != {"name", "items"}:
        raise ValueError("run plan requires name and items")
    if not isinstance(data["name"], str) or not data["name"].strip():
        raise ValueError("run plan name must be non-empty text")
    if not isinstance(data["items"], list) or not data["items"]:
        raise ValueError("run plan items must be a non-empty list")
    entries = []
    for index, value in enumerate(data["items"], 1):
        if (
            not isinstance(value, dict)
            or "name" not in value
            or value.keys() - {"name", "wait_after_seconds"}
            or not isinstance(value["name"], str)
            or not value["name"].strip()
        ):
            raise ValueError(f"invalid run plan item {index}")
        seconds = value.get("wait_after_seconds", 0)
        validate_plan_wait(seconds)
        entries.append(SavedPlanEntry(value["name"], seconds))
    return SavedRunPlan(data["name"], tuple(entries))


def saved_run_plan_data(plan: SavedRunPlan) -> dict:
    """转换为可保存和跨进程传输的流程数据。"""
    return {
        "name": plan.name,
        "items": [
            {"name": entry.name, "wait_after_seconds": entry.wait_after_seconds}
            for entry in plan.entries
        ],
    }


def save_run_plan(workspace: Path, plan: SavedRunPlan) -> None:
    """先写完整临时文件再替换，写入失败时保留旧流程。"""
    data = saved_run_plan_data(plan)
    parse_saved_run_plan(data)
    folder = workspace / ".star"
    folder.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=folder, delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, folder / "run-plan.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
