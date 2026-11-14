"""验证本地桌面平台 composition 只装配原生窗口运行时。"""

from __future__ import annotations

from game_automation.platform.local_desktop import composition
from game_automation.portable.application.local_control import LocalControlApplication
from tests.support.function_tasks import function_task


def test_dry_run_composition_does_not_open_native_runtime(monkeypatch) -> None:
    """模拟运行不创建原生工厂，也不接收屏幕绝对坐标设备。"""
    captured = {}

    def fake_run_task(*args, **kwargs):
        """记录传给运行用例的参数。"""
        captured["args"] = args
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_task", fake_run_task)
    task = function_task("plain", "ctx.click(Point(1, 2))")

    assert composition.run_task_on_local_desktop(task, dry_run=True) == "result"
    assert captured["args"] == (task,)
    assert captured["kwargs"]["dry_run"] is True
    assert captured["kwargs"]["real_runtime_factory"] is None
    assert "real_device_factory" not in captured["kwargs"]
    assert "target_application" not in captured["kwargs"]


def test_real_composition_uses_native_runtime_factory(monkeypatch) -> None:
    """真实运行只注入原生窗口工厂。"""
    captured = {}
    sentinel = object()

    def fake_run_task(*args, **kwargs):
        """记录真实运行参数。"""
        captured["kwargs"] = kwargs
        return "result"

    monkeypatch.setattr(composition, "run_task", fake_run_task)
    monkeypatch.setattr(
        composition, "build_native_runtime_factory", lambda project_root: sentinel
    )
    task = function_task("plain", "ctx.click(Point(1, 2))")

    assert composition.run_task_on_local_desktop(task, dry_run=False) == "result"
    assert captured["kwargs"]["real_runtime_factory"] is sentinel
    assert "real_device_factory" not in captured["kwargs"]
    assert "target_application" not in captured["kwargs"]


def test_control_application_binds_catalog_and_native_factory(
    monkeypatch, tmp_path
) -> None:
    """控制应用使用工作区任务目录和原生工厂，不装配桌面输入。"""
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "demo.py").write_text(
        "TASK = {'name': 'demo'}\ndef run(ctx):\n    ctx.click(Point(1, 2))\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        composition, "build_native_runtime_factory", lambda project_root: "native"
    )

    app = composition.build_local_control_application(project_root=tmp_path)

    assert isinstance(app, LocalControlApplication)
    assert app.list_tasks() == ("demo",)
    assert app._real_runtime_factory == "native"
    assert not hasattr(app, "_real_device_factory")
