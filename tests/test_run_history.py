"""验证控制台运行记录跨会话保留及失败诊断。

通过公开应用接口和本地存储 adapter 检查可观察结果；不访问桌面或推断业务完成。
"""

import threading
import time

import pytest

from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.domain import ImageTarget, ImageTemplate, Click, Script, ScreenWindow, Wait
from game_automation.portable.scripts_manager.catalog import ScriptCatalog


def wait_finished(app):
    """等待后台会话进入终态，避免测试依赖调度顺序。"""
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        status = app.current_script_run()
        if not status.running:
            return status
        time.sleep(0.005)
    pytest.fail("后台运行没有结束")


def test_history_survives_new_application_and_keeps_both_runs(tmp_path):
    """第二次运行与应用重建后仍能分别读取前次结果和输出。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    script = Script(name="等待示例", window=ScreenWindow(), steps=(Wait(0.0),))
    catalog = ScriptCatalog((script,))
    store = SqliteRunHistoryStore(tmp_path / "runs.sqlite3")
    app = LocalControlApplication(catalog=catalog, project_root=tmp_path, run_history=store)
    for _ in range(2):
        app.start_named_script(script.name, dry_run=True)
        assert wait_finished(app).finish_reason == "completed"

    restored = LocalControlApplication(project_root=tmp_path, run_history=SqliteRunHistoryStore(store.path))
    records = restored.list_run_history()
    assert len(records) == 2
    assert records[0]["id"] != records[1]["id"]
    assert all(item["started_at"] and item["ended_at"] for item in records)
    detail = restored.read_run_history(records[-1]["id"])
    assert detail["summary"]["name"] == script.name
    assert detail["summary"]["dry_run"] is True
    assert "wait 0.0s" in "".join(r["data"] for r in detail["records"] if r["kind"] == "stdout")
    assert any(r["kind"] == "event" and r["data"]["type"] == "run_finished" for r in detail["records"])
    assert all(r["recorded_at"] for r in detail["records"])


def test_cancel_is_saved_with_request_and_unfinished_step(tmp_path):
    """取消要保存请求、实际终态及发生取消时的步骤，重复启动不产生假运行。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    entered, release = threading.Event(), threading.Event()

    class BlockingDevice:
        """阻塞等待以便通过公开停止接口模拟用户取消。"""

        def wait(self, seconds):
            """等测试释放后再到取消边界。"""
            entered.set()
            assert release.wait(3)

    script = Script("慢等待", ScreenWindow(), (Wait(1),))
    store = SqliteRunHistoryStore(tmp_path / "runs.sqlite3")
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path,
                                  run_history=store, real_device_factory=BlockingDevice)
    app.start_named_script(script.name, dry_run=False)
    try:
        assert entered.wait(2)
        app.start_named_script(script.name, dry_run=False)
        assert len(app.list_run_history()) == 1
        assert app.list_run_history()[0]["running"] is True
        app.stop_running_script()
    finally:
        release.set()
    assert wait_finished(app).finish_reason == "cancelled"
    detail = app.read_run_history(app.list_run_history()[0]["id"])
    assert detail["summary"]["finish_reason"] == "cancelled"
    assert detail["summary"]["exit_code"] == 130
    assert detail["summary"]["last_step"].startswith("1 Wait")
    assert any(r["kind"] == "stop_requested" for r in detail["records"])


@pytest.mark.parametrize("mode", ["missing_script", "missing_image", "device_error"])
def test_history_preserves_distinct_failure_results(tmp_path, mode):
    """配置、条件停止和平台异常在持久历史中不能都变成成功。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    script = Script("找图片", ScreenWindow(), (Click(ImageTarget(ImageTemplate("absent.png"))),))
    if mode == "device_error":
        script = Script("设备故障", ScreenWindow(), (Wait(0),))

    def broken_device():
        """模拟平台初始化的意外故障。"""
        raise RuntimeError("设备断开")

    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path,
                                  run_history=SqliteRunHistoryStore(tmp_path / "runs.sqlite3"),
                                  real_device_factory=broken_device)
    app.start_named_script("不存在" if mode == "missing_script" else script.name, dry_run=mode != "device_error")
    status = wait_finished(app)
    expected = {"missing_script": "script_not_found", "missing_image": "stopped_unmet_condition", "device_error": "setup_failed"}[mode]
    assert status.finish_reason == expected
    record = app.list_run_history()[0]
    assert record["finish_reason"] == expected
    assert record["exit_code"] == status.exit_code
    assert record["error"] == status.stderr


def test_unfinished_log_survives_without_fabricated_completion_and_workspace_isolation(tmp_path):
    """只写入起点而没有终态时，新实例仍保留日志并显示尚无结束记录。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    path = tmp_path / "one" / ".star" / "runs.sqlite3"
    store = SqliteRunHistoryStore(path)
    run_id = store.begin("异常退出的运行", False)
    store.append(run_id, "stdout", "最后一条记录\n")
    restored = SqliteRunHistoryStore(path)
    assert restored.read_run(run_id)["records"][0]["data"] == "最后一条记录\n"
    summary = restored.list_runs()[0]
    assert summary["finish_reason"] == "unfinished"
    assert summary["exit_code"] is None
    assert summary["ended_at"] is None
    other = SqliteRunHistoryStore(tmp_path / "two" / ".star" / "runs.sqlite3")
    assert other.list_runs() == ()
    assert not other.path.exists()
    with pytest.raises(LookupError):
        restored.read_run("../runs.sqlite3")


def test_unwritable_log_rejects_start_before_device_input(tmp_path):
    """开始前无法保存日志时直接提示，不能一边执行一边丢失整次记录。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    blocker = tmp_path / "not-a-directory"
    blocker.write_text("blocked")

    def reject_device():
        """验证日志失败发生在桌面初始化之前。"""
        pytest.fail("不应接触真实设备")

    script = Script("wait", ScreenWindow(), (Wait(0),))
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path,
                                  run_history=SqliteRunHistoryStore(blocker / "runs.sqlite3"),
                                  real_device_factory=reject_device)
    result = app.start_named_script(script.name, dry_run=False)
    assert not result.running
    assert result.finish_reason == "setup_failed"
    assert "无法建立运行日志" in result.stderr
    assert app.current_script_run() == result


def test_storage_failure_during_run_keeps_result_and_warns(tmp_path):
    """中途存储失效时保留实际结果与内存日志，并明确警告历史可能不完整。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    class FailingStore(SqliteRunHistoryStore):
        """只在已经开始后的追加阶段失败。"""

        def append(self, run_id, kind, data):
            """模拟磁盘写入故障。"""
            raise OSError("磁盘已满")

    script = Script("wait", ScreenWindow(), (Wait(0),))
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path,
                                  run_history=FailingStore(tmp_path / "runs.sqlite3"))
    app.start_named_script(script.name, dry_run=True)
    status = wait_finished(app)
    assert status.finish_reason == "completed"
    assert "日志保存中断" in status.stderr
    assert app.list_run_history()[0]["finish_reason"] == "unfinished"


def test_imported_snapshot_keeps_unknown_times_unknown(tmp_path):
    """抢救旧日志时保留原始内容、取消结果和未知的原运行时间。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    store = SqliteRunHistoryStore(tmp_path / "runs.sqlite3")
    run_id = store.import_snapshot("旧运行", False, {
        "stdout": "已有日志\n", "stderr": "script run cancelled\n",
        "finish_reason": "cancelled", "exit_code": 130, "events": [],
    })
    detail = store.read_run(run_id)
    assert detail["summary"]["source"] == "recovered"
    assert detail["summary"]["started_at"] is None
    assert detail["summary"]["finish_reason"] == "cancelled"
    assert detail["records"][0]["data"] == "已有日志\n"
    assert all(r["recorded_at"] is None for r in detail["records"])


def test_history_cli_lists_exports_and_reports_missing_record(tmp_path, capsys):
    """命令行能读取同一工作区历史、导出完整记录并对不存在记录返回非零。"""
    import json
    from game_automation.platform.local_desktop.entrypoints.cli import main
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    base = ["--workspace", str(tmp_path), "history"]
    assert main(base) == 0
    assert "暂无" in capsys.readouterr().out
    assert not (tmp_path / ".star").exists()
    store = SqliteRunHistoryStore(tmp_path / ".star" / "runs.sqlite3")
    run_id = store.begin("查询示例", True)
    store.append(run_id, "stderr", "目标图片没有出现\n")
    store.finish(run_id, 0, "stopped_unmet_condition")
    assert main(base) == 0
    assert "stopped_unmet_condition" in capsys.readouterr().out
    assert main([*base, run_id]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["records"][0]["data"] == "目标图片没有出现\n"
    assert main([*base, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["runs"][0]["id"] == run_id
    assert main([*base, "missing"]) == 1
    assert "不存在" in capsys.readouterr().err


def test_unexpected_action_failure_is_saved_and_allows_next_run(tmp_path):
    """动作意外异常仍保存失败及异常类型，下一次正常运行保留独立记录。"""
    from game_automation.portable.adapters.sqlite_run_history import SqliteRunHistoryStore

    class BrokenDevice:
        """提供会在动作期间失败的输入替身。"""

        def wait(self, seconds):
            """模拟无法预知的底层动作错误。"""
            raise IndexError("动作状态失效")

    script = Script("wait", ScreenWindow(), (Wait(0),))
    app = LocalControlApplication(catalog=ScriptCatalog((script,)), project_root=tmp_path,
                                  run_history=SqliteRunHistoryStore(tmp_path / "runs.sqlite3"),
                                  real_device_factory=BrokenDevice)
    app.start_named_script(script.name, dry_run=False)
    assert wait_finished(app).finish_reason == "failed"
    assert "IndexError" in app.list_run_history()[0]["error"]
    app.start_named_script(script.name, dry_run=True)
    assert wait_finished(app).finish_reason == "completed"
    assert [r["finish_reason"] for r in app.list_run_history()] == ["completed", "failed"]
