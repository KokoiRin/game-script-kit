"""验证保存流程的配置、桌面编排、任务后等待和取消。

测试使用临时工作区与替身执行入口，真实设备行为由窗口 adapter 测试覆盖。
"""

import json
from pathlib import Path
from time import monotonic, sleep

import pytest

from game_automation.platform.local_desktop.entrypoints import cli
from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
    DesktopBackend,
)
from game_automation.portable.application import local_control
from game_automation.portable.application.project_run_plan import load_saved_run_plan
from game_automation.portable.application.run_plan import (
    TaskPlanItem,
    TaskPlanRunResult,
    run_task_plan,
)
from game_automation.portable.application.task_run import TaskRunResult
from tests.support.function_tasks import function_task


def save_plan(root, items):
    """创建同一工作区的两个任务与流程配置。"""
    (root / "scripts").mkdir(exist_ok=True)
    for name in ("first", "second"):
        (root / "scripts" / f"{name}.py").write_text(
            f'TASK = {{"name": "{name}"}}\ndef run(ctx): ctx.wait(0)\n'
        )
    (root / ".star").mkdir(exist_ok=True)
    (root / ".star/run-plan.json").write_text(
        json.dumps({"name": "daily", "items": items})
    )


def wait_done(backend):
    """有界等待后台整套流程结束。"""
    deadline = monotonic() + 3
    while monotonic() < deadline:
        status = backend.dispatch("script.status", {})
        if not status["running"]:
            return status
        sleep(0.01)
    raise AssertionError("plan did not finish")


def test_saved_plan_runs_in_cli_and_desktop_with_simulated_delay(tmp_path, capsys):
    """两个入口按顺序执行，模拟六百秒等待立即结束。"""
    save_plan(
        tmp_path, [{"name": "first", "wait_after_seconds": 600}, {"name": "second"}]
    )
    assert (
        cli.main(["--workspace", str(tmp_path), "run-plan", "--saved", "--dry-run"])
        == 0
    )
    assert "600" in capsys.readouterr().out
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        listing = backend.dispatch("script.list", {})
        assert listing["plan"]["name"] == "daily"
        assert "600" in listing["plan"]["steps"][0]
        backend.dispatch("plan.start", {"dry_run": True})
        status = wait_done(backend)
        assert status["finish_reason"] == "completed"
        assert (
            status["stdout"].index("开始任务 first")
            < status["stdout"].index("任务后等待 600")
            < status["stdout"].index("开始任务 second")
        )
    finally:
        assert backend.close()


def test_stop_during_post_task_wait_prevents_later_task(tmp_path, monkeypatch):
    """真实时长等待收到停止立即结束，并释放整套流程运行槽。"""
    save_plan(
        tmp_path, [{"name": "first", "wait_after_seconds": 600}, {"name": "second"}]
    )
    calls = []

    def fake_run(task, **kwargs):
        """记录任务调用，代替所有设备与窗口操作。"""
        calls.append(task.name)
        return TaskRunResult(0)

    monkeypatch.setattr(local_control, "run_task", fake_run)
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        backend.dispatch("plan.start", {"dry_run": False})
        deadline = monotonic() + 2
        while (
            monotonic() < deadline
            and "任务后等待 600" not in backend.dispatch("script.status", {})["stdout"]
        ):
            sleep(0.01)
        assert "任务后等待 600" in backend.dispatch("script.status", {})["stdout"]
        with pytest.raises(RuntimeError, match="running"):
            backend.dispatch("script.start", {"name": "second", "dry_run": True})
        with pytest.raises(RuntimeError, match="running"):
            backend.dispatch("plan.start", {"dry_run": True})
        with pytest.raises(RuntimeError, match="running"):
            backend.dispatch(
                "plan.save", {"plan": {"name": "edit", "items": [{"name": "second"}]}}
            )
        backend.dispatch("script.stop", {})
        assert wait_done(backend)["finish_reason"] == "cancelled"
        assert calls == ["first"]
        backend.dispatch("script.start", {"name": "second", "dry_run": True})
        assert wait_done(backend)["finish_reason"] == "completed"
    finally:
        assert backend.close()


@pytest.mark.parametrize("value", [-1, True, "600", float("inf"), float("nan")])
def test_invalid_wait_rejected_before_execution(tmp_path, value):
    """无效等待在读取计划时报告配置错误。"""
    save_plan(tmp_path, [{"name": "first", "wait_after_seconds": value}])
    with pytest.raises(ValueError, match="wait_after_seconds"):
        load_saved_run_plan(tmp_path)


def test_invalid_later_task_prevents_any_execution(tmp_path, monkeypatch):
    """后续名称错误在开始首项之前被指出，单任务列表继续可用。"""
    save_plan(tmp_path, [{"name": "first"}, {"name": "missing"}])
    calls = []
    monkeypatch.setattr(
        local_control, "run_task", lambda *args, **kwargs: calls.append(args)
    )
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        result = backend.dispatch("plan.start", {"dry_run": True})
        assert result["finish_reason"] == "task_not_found"
        assert calls == []
        listing = backend.dispatch("script.list", {})
        assert set(listing["scripts"]) == {"first", "second"}
        assert listing["plan_error"]
    finally:
        assert backend.close()


def test_skipped_task_continues_without_post_wait():
    """明确跳过的任务保留记录，继续后续项并略过其任务后等待。"""
    items = [
        TaskPlanItem(name, function_task(name, "pass"), wait_after_seconds=600)
        for name in ("first", "second")
    ]
    waits = []
    result = run_task_plan(
        items,
        run_item=lambda item: TaskPlanRunResult(
            0, "skipped" if item.name == "first" else "completed"
        ),
        wait=lambda seconds: waits.append(seconds) or True,
    )
    assert result.finish_reason == "completed"
    assert [item.finish_reason for item in result.items] == ["skipped", "completed"]
    assert waits == [600]


def test_task_skip_maps_to_explicit_run_result(tmp_path):
    """Python 任务的跳过信号映射为可继续编排的执行结果。"""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/skip.py").write_text(
        'from game_automation.task import TaskSkipped\nTASK = {"name": "skip"}\ndef run(ctx): raise TaskSkipped("not available")\n'
    )
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        backend.dispatch("script.start", {"name": "skip", "dry_run": True})
        status = wait_done(backend)
        assert (status["exit_code"], status["finish_reason"]) == (0, "skipped")
        assert "not available" in status["stdout"]
    finally:
        assert backend.close()


@pytest.mark.parametrize("reason", ["failed", "cancelled", "cleanup_failed"])
def test_failure_stops_before_wait_and_next_item(reason):
    """失败、取消或清理故障均阻止任务后等待及下一项。"""
    items = [
        TaskPlanItem(name, function_task(name, "pass"), wait_after_seconds=600)
        for name in ("first", "second")
    ]
    calls, waits = [], []

    def fail(item):
        """记录首项并返回指定失败原因。"""
        calls.append(item.name)
        return TaskPlanRunResult(130 if reason == "cancelled" else 1, reason)

    result = run_task_plan(
        items, run_item=fail, wait=lambda seconds: waits.append(seconds) or True
    )
    assert result.finish_reason == reason
    assert calls == ["first"] and waits == []


def test_malformed_plan_keeps_single_tasks_available(tmp_path):
    """流程配置损坏时保留单任务列表并展示流程错误。"""
    save_plan(tmp_path, [{"name": "first"}])
    (tmp_path / ".star/run-plan.json").write_text("{")
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        listing = backend.dispatch("script.list", {})
        assert listing["plan"] == {} and listing["plan_error"]
        backend.dispatch("script.start", {"name": "first", "dry_run": True})
        assert wait_done(backend)["finish_reason"] == "completed"
    finally:
        assert backend.close()


def test_editor_saves_order_duplicates_and_wait_across_reload(tmp_path):
    """编辑后的顺序、重复项与等待时长经重载和执行仍保持一致。"""
    save_plan(tmp_path, [{"name": "first"}])
    backend = DesktopBackend(tmp_path, preparation=object())
    plan = {
        "name": "角色日常",
        "items": [
            {"name": "second"},
            {"name": "first", "wait_after_seconds": 600},
            {"name": "second"},
        ],
    }
    try:
        backend.dispatch("plan.save", {"plan": plan})
        listing = backend.dispatch("script.reload", {})
        assert listing["plan"]["name"] == "角色日常"
        assert [item["name"] for item in listing["plan"]["items"]] == [
            "second",
            "first",
            "second",
        ]
        assert listing["plan"]["items"][1]["wait_after_seconds"] == 600
        backend.dispatch("plan.start", {"dry_run": True})
        status = wait_done(backend)
        assert status["finish_reason"] == "completed"
        assert status["stdout"].count("开始任务 second") == 2
        summary = json.loads(
            (Path(status["artifacts_path"]) / "summary.json").read_text()
        )
        assert [item["index"] for item in summary["items"]] == [1, 2, 3]
    finally:
        assert backend.close()


@pytest.mark.parametrize(
    "items", [[], [{"name": "missing"}], [{"name": "first", "wait_after_seconds": -1}]]
)
def test_invalid_editor_save_preserves_previous_plan(tmp_path, items):
    """无效编辑不覆盖已保存的可运行流程。"""
    save_plan(tmp_path, [{"name": "first"}])
    original = (tmp_path / ".star/run-plan.json").read_bytes()
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        with pytest.raises((ValueError, LookupError)):
            backend.dispatch("plan.save", {"plan": {"name": "bad", "items": items}})
        assert (tmp_path / ".star/run-plan.json").read_bytes() == original
    finally:
        assert backend.close()


def test_start_submitted_plan_runs_snapshot_without_rereading(tmp_path, monkeypatch):
    """当前草稿一次提交后运行同一快照，后续文件变化不影响顺序。"""
    save_plan(tmp_path, [{"name": "first"}])
    original_save = local_control.save_run_plan

    def save_then_change(root, plan):
        """模拟原子保存成功后外部修改配置。"""
        original_save(root, plan)
        (root / ".star/run-plan.json").write_text("{")

    monkeypatch.setattr(local_control, "save_run_plan", save_then_change)
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        backend.dispatch(
            "plan.start",
            {
                "dry_run": True,
                "plan": {
                    "name": "draft",
                    "items": [{"name": "second"}, {"name": "second"}],
                },
            },
        )
        status = wait_done(backend)
        assert status["finish_reason"] == "completed"
        assert status["stdout"].count("开始任务 second") == 2
    finally:
        assert backend.close()


def test_repeated_task_second_failure_has_distinct_record(tmp_path):
    """同名任务第二次失败时标记第二项，第三项保持未执行。"""
    save_plan(tmp_path, [{"name": "first"}, {"name": "first"}, {"name": "second"}])
    counter = tmp_path / "counter.txt"
    (tmp_path / "scripts/first.py").write_text(
        'from pathlib import Path\nTASK = {"name": "first"}\n'
        "def run(ctx):\n"
        f"    path = Path({str(counter)!r})\n"
        "    count = int(path.read_text()) + 1 if path.exists() else 1\n"
        "    path.write_text(str(count))\n"
        "    if count == 2:\n"
        '        raise RuntimeError("second occurrence failed")\n'
    )
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        backend.dispatch("plan.start", {"dry_run": True})
        status = wait_done(backend)
        summary = json.loads(
            (Path(status["artifacts_path"]) / "summary.json").read_text()
        )
        assert [item["finish_reason"] for item in summary["items"]] == [
            "completed",
            "failed",
            "pending",
        ]
        assert "second occurrence failed" in summary["items"][1]["traceback"]
        assert "开始任务 second" not in status["stdout"]
    finally:
        assert backend.close()


def test_invalid_submitted_plan_preserves_disk_and_never_starts(tmp_path):
    """后续无效条目使本次启动失败并保留旧配置。"""
    save_plan(tmp_path, [{"name": "first"}])
    original = (tmp_path / ".star/run-plan.json").read_bytes()
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        status = backend.dispatch(
            "plan.start",
            {
                "dry_run": True,
                "plan": {
                    "name": "bad",
                    "items": [{"name": "first"}, {"name": "missing"}],
                },
            },
        )
        assert status["finish_reason"] == "task_not_found"
        assert "开始任务" not in status["stdout"]
        assert (tmp_path / ".star/run-plan.json").read_bytes() == original
    finally:
        assert backend.close()
