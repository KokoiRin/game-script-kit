"""验证函数任务通过 CLI 和原生后台公开协议发现、执行和停止。

测试创建独立工作区，使用真实应用装配及 dry-run，不连接真实桌面。
"""

from time import monotonic, sleep

from game_automation.platform.local_desktop.entrypoints import cli
from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
    DesktopBackend,
)


def write_task(workspace, source, *, filename="flow.py"):
    """在测试工作区保存一份普通 Python 任务。"""
    directory = workspace / "scripts"
    directory.mkdir(exist_ok=True)
    (workspace / "assets").mkdir(exist_ok=True)
    path = directory / filename
    path.write_text(source)
    return path


def wait_finished(backend):
    """通过公开状态查询等待后台进入终态。"""
    deadline = monotonic() + 3
    while monotonic() < deadline:
        status = backend.dispatch("script.status", {})
        if not status["running"]:
            return status
        sleep(0.01)
    raise AssertionError("function task did not finish")


def test_cli_function_list_details_run_and_plan(tmp_path, capsys):
    """CLI 所有运行入口能使用同一份函数任务且查询没有执行副作用。"""
    marker = tmp_path / "executed"
    write_task(
        tmp_path,
        f'''from pathlib import Path

TASK = {{"name": "函数流程"}}
Path({str(marker)!r}).write_text("executed")

def run(ctx):
    """直接执行 Python 循环与分支。"""
    for index in range(3):
        if index == 1:
            continue
        ctx.wait(0)
''',
    )
    args = ["--workspace", str(tmp_path)]

    assert cli.main([*args, "list"]) == 0
    assert "函数流程" in capsys.readouterr().out
    assert cli.main([*args, "details", "函数流程"]) == 0
    assert "flow.py" in capsys.readouterr().out
    assert not marker.exists()

    assert cli.main([*args, "run", "函数流程", "--dry-run"]) == 0
    assert marker.read_text() == "executed"
    assert capsys.readouterr().out.count("wait") == 2
    assert cli.main([*args, "run-plan", "函数流程", "函数流程", "--dry-run"]) == 0


def test_native_protocol_runs_stops_and_restarts_function_task(tmp_path):
    """原生运行页协议可停止纯 Python 循环并在取消后重新运行。"""
    write_task(
        tmp_path,
        '''TASK = {"name": "持续计算"}

def run(ctx):
    """在无动作调用的循环中等待用户取消。"""
    while True: pass
''',
    )
    write_task(
        tmp_path,
        '''TASK = {"name": "有限流程"}

def run(ctx):
    """运行一份会正常返回的任务。"""
    ctx.wait(0)
''',
        filename="finite.py",
    )
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        assert set(backend.dispatch("script.list", {})["scripts"]) == {
            "持续计算",
            "有限流程",
        }
        details = backend.dispatch("script.details", {"name": "持续计算"})
        assert details["exit_code"] == 0
        backend.dispatch("script.start", {"name": "持续计算", "dry_run": True})
        backend.dispatch("script.stop", {})
        stopped = wait_finished(backend)
        assert (stopped["exit_code"], stopped["finish_reason"]) == (130, "cancelled")

        backend.dispatch("script.start", {"name": "有限流程", "dry_run": True})
        finished = wait_finished(backend)
        assert (finished["exit_code"], finished["finish_reason"]) == (0, "completed")
        assert "wait" in finished["stdout"]
    finally:
        assert backend.close()


def test_native_protocol_ignores_json_and_keeps_python_task_available(
    tmp_path,
):
    """JSON 文件不是任务；有效 Python 任务仍可模拟运行。"""
    write_task(tmp_path, 'TASK = {"name": "valid"}\ndef run(ctx): ctx.wait(0)\n')
    (tmp_path / "scripts" / "old.json").write_text(
        '{"name": "old", "steps": [{"wait": 60}]}'
    )
    backend = DesktopBackend(tmp_path, preparation=object())
    try:
        listing = backend.dispatch("script.list", {})
        assert listing["scripts"] == ["valid"]
        assert listing["errors"] == []
        backend.dispatch("script.start", {"name": "valid", "dry_run": True})
        assert wait_finished(backend)["finish_reason"] == "completed"
    finally:
        assert backend.close()
