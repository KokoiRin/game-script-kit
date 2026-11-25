"""验证控制台跟随目标来自任务声明或真实运行绑定。

本模块使用目录与窗口替身，不激活应用或读写真实桌面。
"""

import json
import threading
from contextlib import contextmanager

import pytest

from game_automation.platform.local_desktop.entrypoints.desktop_backend import (
    DesktopBackend,
)
from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.application.runtime_ports import (
    RuntimePorts,
    RuntimeWindowIdentity,
)
from game_automation.portable.application.task_catalog import TaskCatalog
from game_automation.portable.domain import UnboundWindow
from game_automation.portable.domain.task import TaskTarget
from tests.support.function_tasks import function_task


def control_for(tmp_path, targets, **kwargs):
    """为各个目标建立无需真实设备的任务目录。"""
    return LocalControlApplication(
        catalog=TaskCatalog(
            tuple(
                function_task(name, "ctx.wait(0)", target=target)
                for name, target in targets.items()
            )
        ),
        project_root=tmp_path,
        **kwargs,
    )


def target(title="Main"):
    """声明固定尺寸的窗口目标。"""
    return TaskTarget("Fixture", title, 100, 80, "macos-window-background")


def test_idle_companion_uses_unique_or_explicit_task_target(tmp_path):
    """默认观察页只在共同目标唯一时跟随，显式选择消除歧义。"""
    first, second = target(), target("Other")
    app = control_for(tmp_path, {"one": first, "two": first, "demo": None})
    assert app.companion_selection().target == first
    app = control_for(tmp_path, {"one": first, "two": second})
    assert app.companion_selection().target is None
    assert app.companion_selection("two").target == second
    assert app.companion_selection("one").target == first
    with pytest.raises(LookupError):
        app.companion_selection("missing")


def test_saved_plan_companion_uses_plan_targets(tmp_path):
    """计划目标由保存的任务引用选择，多个目标时保持未绑定。"""
    first, second = target(), target("Other")
    app = control_for(tmp_path, {"one": first, "two": second})
    (tmp_path / ".star").mkdir()
    path = tmp_path / ".star/run-plan.json"
    path.write_text(json.dumps({"name": "daily", "items": [{"name": "one"}]}))
    assert app.companion_selection(use_saved_plan=True).target == first
    path.write_text(
        json.dumps({"name": "daily", "items": [{"name": "one"}, {"name": "two"}]})
    )
    assert app.companion_selection(use_saved_plan=True).target is None


def test_backend_resolves_idle_target_without_preparation_selection(tmp_path):
    """单一查询在默认观察页返回具体身份，失败时清空绑定并保留诊断。"""
    wanted = target()
    app = control_for(tmp_path, {"one": wanted})
    calls = []

    def resolve(value):
        """记录唯一目标解析并返回实际窗口编号。"""
        calls.append(value)
        return RuntimeWindowIdentity(42, 900)

    with_backend = DesktopBackend(
        tmp_path,
        preparation=object(),
        control_factory=lambda: app,
        companion_resolver=resolve,
    )
    try:
        assert with_backend.dispatch("companion.target", {}) == {
            "target": {"pid": 42, "window_number": 900}
        }
        assert calls == [wanted]
        assert (
            with_backend.dispatch("companion.target", {"file": "missing"})["target"]
            is None
        )
        with pytest.raises(ValueError):
            with_backend.dispatch("companion.target", {"use_saved_plan": "true"})
    finally:
        with_backend.close()


def test_running_companion_publishes_actual_runtime_binding(tmp_path):
    """运行中的真实绑定优先于界面选择，关闭后恢复空闲声明解析。"""
    ready, release = threading.Event(), threading.Event()
    identity = RuntimeWindowIdentity(77, 999)

    class Device:
        def wait(self, seconds):
            """固定运行在真实会话内部直到测试允许结束。"""
            ready.set()
            assert release.wait(5)

    class Factory:
        @contextmanager
        def open(self, *args):
            """模拟打开已确定编号的原生会话。"""
            yield RuntimePorts(UnboundWindow(), Device(), window_identity=identity)

    app = control_for(
        tmp_path,
        {"one": target(), "two": target("Other")},
        real_runtime_factory=Factory(),
    )
    session = DesktopBackend(
        tmp_path,
        preparation=object(),
        control_factory=lambda: app,
        companion_resolver=lambda value: RuntimeWindowIdentity(1, 2),
    )
    try:
        assert app.start_named_task("one", dry_run=False).running
        assert ready.wait(5)
        assert session.dispatch("companion.target", {"file": "two"}) == {
            "target": {"pid": 77, "window_number": 999}
        }
        release.set()
        assert app.wait_for_task_stop(5)
        assert session.dispatch("companion.target", {"file": "two"}) == {
            "target": {"pid": 1, "window_number": 2}
        }
    finally:
        release.set()
        session.close()


def test_plan_wait_keeps_last_verified_companion_until_terminal(tmp_path):
    """任务后等待保持跟随，停止后撤销运行身份并采用空闲目标。"""
    closed = threading.Event()
    identity = RuntimeWindowIdentity(77, 999)

    class Device:
        def wait(self, seconds):
            """让任务本身立即完成。"""

    class Factory:
        @contextmanager
        def open(self, *args):
            """发布真实身份并在退出时通知等待阶段。"""
            try:
                yield RuntimePorts(UnboundWindow(), Device(), window_identity=identity)
            finally:
                closed.set()

    app = control_for(tmp_path, {"one": target()}, real_runtime_factory=Factory())
    (tmp_path / ".star").mkdir()
    (tmp_path / ".star/run-plan.json").write_text(
        json.dumps(
            {"name": "daily", "items": [{"name": "one", "wait_after_seconds": 10}]}
        )
    )
    try:
        app.start_saved_plan(dry_run=False)
        assert closed.wait(5)
        assert app.companion_selection().window == identity
        assert app.companion_selection().running
        app.stop_running_task()
        assert app.wait_for_task_stop(5)
        assert app.companion_selection().window is None
        assert app.companion_selection().target == target()
    finally:
        app.stop_running_task()
        app.wait_for_task_stop(5)
