"""验证原生桌面后台协议、单帧传输和退出回收。

本 module 用内存图像与设备替身验证进程边界，不启动 GUI 或真实桌面。
"""

import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

import pytest

from game_automation.platform.local_desktop.entrypoints.desktop_backend import DesktopBackend, WorkspaceLock, run_stdio
from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.domain import Script, ScreenWindow, Wait
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
from tests.test_preparation import PreparationBackend
from game_automation.portable.preparation.service import PreparationService
from game_automation.portable.engine.ports import InputDevice


@pytest.fixture
def backend(tmp_path):
    """装配可验证生命周期的后台会话。"""
    device = PreparationBackend()
    prep = PreparationService(windows=device, capture=device, images=device, templates=device)
    control = LocalControlApplication(
        catalog=ScriptCatalog((Script("sample", ScreenWindow(), (Wait(0),)),)), project_root=tmp_path,
    )
    session = DesktopBackend(tmp_path, preparation=prep, control_factory=lambda: control)
    try:
        yield session, control
    finally:
        session.close()


def test_backend_transfers_only_frame_path_and_cleans_cache(backend):
    """截图不经 JSON Base64 复制，重截和退出均回收旧文件。"""
    session, _ = backend
    first = session.dispatch("preparation.capture", {"application": "Game", "window_id": "42:1"})
    path = Path(first["image"]["path"])
    assert path.read_bytes() == b"frame"
    assert "png_base64" not in json.dumps(first)
    assert session.dispatch("preparation.point", {"frame_id": first["id"], "x": 40, "y": 60})["window_relative"] == {"x": 20, "y": 30}
    second = session.dispatch("preparation.capture", {"application": "Game", "window_id": "42:1"})
    assert not path.exists()
    current = Path(second["image"]["path"])
    assert current.exists()
    session.close()
    assert not current.exists()


def test_stdio_survives_bad_requests_and_finishes_after_shutdown(backend):
    """协议错误不崩溃，关闭确认后拒绝处理后续命令。"""
    session, _ = backend
    commands = ["broken", json.dumps({"jsonrpc": "2.0", "id": 1, "method": "session.info"}),
                json.dumps({"jsonrpc": "2.0", "id": 2, "method": "session.shutdown"}),
                json.dumps({"jsonrpc": "2.0", "id": 3, "method": "script.list"})]
    output = io.StringIO()
    assert run_stdio(session, io.StringIO("\n".join(commands) + "\n"), output, io.StringIO()) == 0
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[0]["error"]["code"] == -32700
    assert replies[1]["result"]["protocol"] == 1
    assert replies[2]["result"]["stopping"] is True
    assert len(replies) == 3


def test_background_script_does_not_capture_protocol_output(backend):
    """运行线程重定向日志期间，协议响应仍写入原始输出流。"""
    session, control = backend
    output = io.StringIO()
    commands = [
        {"jsonrpc": "2.0", "id": 1, "method": "script.start", "params": {"name": "sample", "dry_run": True}},
        {"jsonrpc": "2.0", "id": 2, "method": "script.status"},
    ]
    assert run_stdio(session, io.StringIO("\n".join(map(json.dumps, commands)) + "\n"), output, io.StringIO()) == 0
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert [reply["id"] for reply in replies] == [1, 2]
    assert not control.current_script_run().running
    assert control.wait_for_script_stop(0)


def test_workspace_allows_only_one_backend_owner(tmp_path):
    """同一工作区同时只允许一个原生后台持有状态。"""
    with WorkspaceLock(tmp_path):
        with pytest.raises(RuntimeError, match="already"):
            with WorkspaceLock(tmp_path):
                pass
    with WorkspaceLock(tmp_path):
        pass


def test_real_backend_process_exits_on_pipe_eof_and_releases_lock(tmp_path):
    """宿主关闭管道后，真实后台进程自行退出并释放工作区所有权。"""
    command = [sys.executable, "-m", "game_automation.platform.local_desktop.entrypoints.desktop_backend", "--workspace", str(tmp_path)]
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "session.info"}) + "\n"
    result = subprocess.run(command, input=request, capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    info = json.loads(result.stdout)["result"]
    assert info["pid"] == info["process_group"]
    with WorkspaceLock(tmp_path):
        pass


def test_real_backend_rejects_second_process_for_same_workspace(tmp_path):
    """第二个原生进程明确报错，不能并发操作同一任务根。"""
    command = [sys.executable, "-m", "game_automation.platform.local_desktop.entrypoints.desktop_backend", "--workspace", str(tmp_path)]
    request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "session.info"}) + "\n"
    first = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        first.stdin.write(request)
        first.stdin.flush()
        assert json.loads(first.stdout.readline())["result"]["protocol"] == 1
        second = subprocess.run(command, input=request, capture_output=True, text=True, timeout=5)
        assert second.returncode == 1
        assert "already" in second.stderr
    finally:
        first.communicate(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "session.shutdown"}) + "\n", timeout=5)
    assert first.returncode == 0


def test_pipe_eof_cancels_active_wait_and_preserves_protocol_output(tmp_path):
    """正在真实等待时协议仍可响应，宿主断开后线程迅速回收。"""
    entered = threading.Event()

    class Device(InputDevice):
        def wait(self, duration_seconds):
            """模拟实际睡眠，使运行线程在第二个请求时仍存活。"""
            entered.set()
            time.sleep(duration_seconds)

    control = LocalControlApplication(
        catalog=ScriptCatalog((Script("long", ScreenWindow(), (Wait(60),)),)),
        project_root=tmp_path, real_device_factory=Device,
    )
    prep = PreparationBackend()
    session = DesktopBackend(tmp_path,
        preparation=PreparationService(windows=prep, capture=prep, images=prep, templates=prep),
        control_factory=lambda: control)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "script.start", "params": {"name": "long", "dry_run": False}},
        {"jsonrpc": "2.0", "id": 2, "method": "script.status"},
    ]

    class Source(io.StringIO):
        def readline(self, size=-1):
            """首个请求后等待设备进入长等待，再读取状态。"""
            if self.tell() > 0:
                assert entered.wait(1)
            return super().readline(size)

    output = io.StringIO()
    source = Source("\n".join(map(json.dumps, requests)) + "\n")
    started = time.monotonic()
    assert run_stdio(session, source, output, io.StringIO()) == 0
    assert time.monotonic() - started < 1
    replies = [json.loads(line) for line in output.getvalue().splitlines()]
    assert replies[1]["result"]["running"] is True
    assert control.current_script_run().finish_reason == "cancelled"
    assert control.wait_for_script_stop(0)


def test_real_backend_termination_signal_releases_ownership(tmp_path):
    """原生宿主发出终止信号时后台执行统一清理，锁不遗留。"""
    command = [sys.executable, "-m", "game_automation.platform.local_desktop.entrypoints.desktop_backend", "--workspace", str(tmp_path)]
    child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        child.stdin.write(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "session.info"}) + "\n")
        child.stdin.flush()
        assert json.loads(child.stdout.readline())["result"]["protocol"] == 1
        child.terminate()
        child.communicate(timeout=5)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait()
    assert child.returncode == 0
    with WorkspaceLock(tmp_path):
        pass
