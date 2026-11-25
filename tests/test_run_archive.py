"""验证桌面持久运行记录与中断截图。

通过真实应用入口和替身窗口验证时序、完整日志与失败隔离，不操作桌面游戏。
"""

import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import pytest

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.task_catalog import TaskCatalog
from game_automation.portable.domain import AreaWindow, Rect
from game_automation.portable.domain.task import TaskTarget
from tests.support.function_tasks import function_task


class Factory:
    """以无输入替身提供可检查生命周期的截图端口。"""

    def __init__(self, *, fail_capture=False, fail_close=False):
        """保存故障开关与截图时序。"""
        self.fail_capture = fail_capture
        self.fail_close = fail_close
        self.closed = False
        self.captured_before_close = False

    def capture(self):
        """模拟当前目标窗口的编码图片。"""
        self.captured_before_close = not self.closed
        if self.closed:
            raise RuntimeError("capture after close")
        if self.fail_capture:
            raise RuntimeError("window disappeared")
        return b"test-png"

    @contextmanager
    def open(self, target, requirements, cancellation, logger):
        """提供无需真实桌面的运行会话。"""
        try:
            yield RuntimePorts(
                AreaWindow(Rect(0, 0, 80, 60)),
                object(),
                capture_diagnostic=self.capture,
            )
        finally:
            self.closed = True
            if self.fail_close:
                raise RuntimeError("close failed")


def run_case(root, body, *, factory=None, dry_run=False):
    """通过桌面应用用例运行任务并读取落盘记录。"""
    task = replace(
        function_task("recorded", body),
        target=TaskTarget("Example", "Example", 80, 60, backend="macos-window"),
    )
    app = LocalControlApplication(
        TaskCatalog((task,)), project_root=root, real_runtime_factory=factory
    )
    app.start_named_task("recorded", dry_run=dry_run)
    assert app.wait_for_task_stop(3)
    status = app.current_task_run()
    folder = Path(status.artifacts_path)
    return status, folder, json.loads((folder / "summary.json").read_text())


@pytest.mark.parametrize(
    "body, reason",
    [
        ('raise RuntimeError("broken")', "failed"),
        ('raise TimeoutError("no dialog")', "timed_out"),
        ('raise TargetNotFound("no button")', "stopped_unmet_condition"),
        ("raise KeyboardInterrupt()", "cancelled"),
    ],
)
def test_interruption_archives_window_before_close(tmp_path, body, reason):
    """失败、超时、条件停止与取消均在关闭当前会话前保存画面。"""
    factory = Factory()
    status, folder, summary = run_case(tmp_path, body, factory=factory)
    assert status.finish_reason == reason
    assert factory.closed and factory.captured_before_close
    assert summary["finish_reason"] == reason
    item = summary["items"][0]
    assert item["finish_reason"] == reason
    assert (folder / item["screenshot"]).read_bytes() == b"test-png"
    assert "run_finished" in (folder / "stdout.log").read_text()


def test_capture_failure_preserves_original_task_error(tmp_path):
    """截图不可用时记录具体原因，原任务错误与清理结果仍保留。"""
    status, folder, summary = run_case(
        tmp_path,
        'raise RuntimeError("original error")',
        factory=Factory(fail_capture=True),
    )
    assert status.finish_reason == "failed"
    assert "original error" in (folder / "stderr.log").read_text()
    assert summary["items"][0]["screenshot_error"] == "window disappeared"


def test_archive_retains_logs_beyond_ui_limit_and_multiple_runs(tmp_path):
    """完整磁盘日志不受界面长度限制，多次运行各自留档。"""
    status, folder, summary = run_case(
        tmp_path, 'print("beginning-marker")\nprint("x" * 300000)', dry_run=True
    )
    assert status.finish_reason == "completed"
    assert "beginning-marker" not in status.stdout
    assert "beginning-marker" in (folder / "stdout.log").read_text()
    assert summary["items"][0]["finish_reason"] == "completed"
    _, another, _ = run_case(tmp_path, "pass", dry_run=True)
    assert another != folder and folder.exists()


def test_dry_run_failure_records_capture_unavailability(tmp_path):
    """模拟运行的失败留下日志与说明，不打开真实窗口。"""
    status, _, summary = run_case(tmp_path, 'raise RuntimeError("fake")', dry_run=True)
    assert status.finish_reason == "failed"
    assert "模拟" in summary["items"][0]["screenshot_error"]


def test_disk_failure_keeps_task_result(tmp_path, monkeypatch):
    """诊断写入失败时执行结果与后台运行槽仍然正确。"""
    original = Path.open

    def unavailable(self, mode="r", *args, **kwargs):
        """仅让日志文件写入模拟磁盘已满。"""
        if self.suffix == ".log" and mode == "a":
            raise OSError("disk full")
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", unavailable)
    status, _, summary = run_case(tmp_path, "pass", dry_run=True)
    assert status.finish_reason == "completed"
    assert "日志保存失败" in status.stderr
    assert summary["finish_reason"] == "completed"


@pytest.mark.parametrize("body", ["pass", 'raise RuntimeError("first error")'])
def test_cleanup_failure_uses_frozen_picture_and_tracebacks(tmp_path, body):
    """源关闭后拒绝截图时，清理失败仍保存关闭前候选画面与堆栈。"""
    factory = Factory(fail_close=True)
    status, folder, summary = run_case(tmp_path, body, factory=factory)
    assert status.finish_reason == "cleanup_failed"
    assert factory.captured_before_close
    item = summary["items"][0]
    assert (folder / item["screenshot"]).read_bytes() == b"test-png"
    assert "close failed" in item["traceback"]
    if "first error" in body:
        assert "first error" in item["traceback"]


def test_cancel_arriving_during_cleanup_keeps_candidate_frame(tmp_path):
    """清理期间才收到取消，最终取消结果仍携带关闭前画面。"""
    from game_automation.portable.application.task_run import run_task

    class Token:
        """提供可在清理期间变化的取消标记。"""

        cancelled = False

        def is_cancelled(self):
            """读取清理回调可改变的标记，使测试能验证关闭期间才到达的取消。"""
            return self.cancelled

    token = Token()
    factory = Factory()
    original = factory.open

    @contextmanager
    def cancel_on_close(*args):
        """在底层已经释放源后发出取消。"""
        with original(*args) as ports:
            yield ports
        token.cancelled = True

    factory.open = cancel_on_close
    task = function_task(
        "late",
        "pass",
        target=TaskTarget("Example", "Example", 80, 60, backend="macos-window"),
    )
    result = run_task(
        task,
        dry_run=False,
        real_runtime_factory=factory,
        cancellation_token=token,
        collect_diagnostics=True,
    )
    assert result.finish_reason == "cancelled"
    assert result.diagnostic.png == b"test-png"
    assert factory.captured_before_close
