"""验证显式原生后端的会话边界；不访问真实桌面。"""

from contextlib import contextmanager
from dataclasses import replace

import pytest

from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.task_run import run_task
from game_automation.portable.domain import AreaWindow, Point, Rect
from game_automation.portable.domain.task import TaskRequirements, TaskTarget
from tests.support.function_tasks import function_task


class Device:
    def __init__(self):
        """收集点击。"""
        self.clicks = []

    def click(self, point):
        """记录全局点。"""
        self.clicks.append(point)


class Factory:
    def __init__(self, *, fail_close=False):
        """记录上下文资源生命周期。"""
        self.device = Device()
        self.closed = False
        self.fail_close = fail_close

    @contextmanager
    def open(self, target, requirements, cancellation, logger):
        """返回统一端口并模拟退出失败。"""
        try:
            yield RuntimePorts(AreaWindow(Rect(100, 200, 80, 60)), self.device)
        finally:
            self.closed = True
            if self.fail_close:
                raise RuntimeError("stream shutdown failed")


def script():
    """创建一个窗口局部点击脚本。"""
    return function_task(
        "native",
        "ctx.click(Point(5, 6))",
        window=AreaWindow(Rect(0, 0, 80, 60)),
        target=TaskTarget("Example", "Game", 80, 60, backend="macos-window"),
    )


def test_explicit_native_backend_owns_all_ports():
    """原生后端只打开一次会话且只增加一次窗口原点。"""
    factory = Factory()
    result = run_task(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "completed"
    assert factory.closed
    assert factory.device.clicks == [Point(105, 206)]


def test_close_failure_never_reports_completed():
    """采集停止失败作为可见失败而非成功。"""
    factory = Factory(fail_close=True)
    result = run_task(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "cleanup_failed"
    assert result.exit_code == 1
    assert "stream shutdown failed" in result.error_message


def test_native_does_not_fallback_to_global_backend():
    """缺少原生工厂必须失败，不访问旧设备。"""
    result = run_task(script(), dry_run=False)
    assert result.finish_reason == "setup_failed"
    assert "desktop fallback is disabled" in result.error_message


def test_dry_run_does_not_open_native_session():
    """模拟模式保留无需平台依赖的执行路径。"""
    result = run_task(script(), dry_run=True)
    assert result.finish_reason == "completed"


def test_real_run_without_native_target_never_opens_factory():
    """没有原生目标时，即使注入了工厂也不会打开会话。"""
    factory = Factory()
    plain = function_task("plain", "ctx.click(Point(1, 2))")
    result = run_task(plain, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "configuration_failed"
    assert factory.closed is False


def test_cancelled_run_closes_and_preserves_cancellation_when_cleanup_fails():
    """取消是主结果，停流失败仍在错误信息中可见。"""
    from game_automation.portable.engine.cancellation import TaskCancelledError

    factory = Factory(fail_close=True)

    def click(point):
        """模拟输入边界收到取消。"""
        raise TaskCancelledError("cancelled by user")

    factory.device.click = click
    result = run_task(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "cancelled"
    assert result.exit_code == 130
    assert "cleanup failed" in result.error_message
    assert factory.closed


def test_setup_failure_after_open_closes_runtime():
    """端口装配失败也必须释放已经打开的会话。"""
    factory = Factory()
    needs_color = replace(script(), requires=TaskRequirements(colors=True))
    result = run_task(needs_color, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "setup_failed"
    assert factory.closed


def test_cleanup_failure_emits_only_failed_terminal_event():
    """终态在关闭之后输出，不能先记录完成再记录停流失败。"""

    class Logger:
        def __init__(self):
            """收集结构化事件。"""
            self.events = []

        def log(self, message):
            """接收普通诊断。"""

        def log_event(self, event):
            """收集终态。"""
            self.events.append(event)

    logger = Logger()
    result = run_task(
        script(),
        dry_run=False,
        real_runtime_factory=Factory(fail_close=True),
        logger=logger,
        emit_step_events=True,
    )
    terminal = [e for e in logger.events if e.event_type == "run_finished"]
    assert result.finish_reason == "cleanup_failed"
    assert [e.status for e in terminal] == ["cleanup_failed"]


def test_sync_and_background_control_use_same_runtime_factory(tmp_path):
    """控制应用的两个入口都注入同一种会话工厂。"""
    from game_automation.portable.application.local_control import (
        LocalControlApplication,
    )
    from game_automation.portable.application.task_catalog import TaskCatalog

    factory = Factory()
    app = LocalControlApplication(
        catalog=TaskCatalog((script(),)),
        project_root=tmp_path,
        real_runtime_factory=factory,
    )
    assert app.run_named_task("native", dry_run=False).finish_reason == "completed"
    app.start_named_task("native", dry_run=False)
    assert app.wait_for_task_stop(2)
    assert app.current_task_run().finish_reason == "completed"
    assert factory.device.clicks == [Point(105, 206), Point(105, 206)]


def test_python_backend_opt_in_and_unknown_backend_fail(tmp_path):
    """原生后端由 TASK 显式选择，拼写错误在发现阶段拒绝。"""
    import pytest

    from game_automation.portable.application.function_task_loader import (
        parse_function_task_source,
    )

    metadata = {
        "name": "sample",
        "target": {
            "application": "Example",
            "window_title": "Game",
            "width": 80,
            "height": 60,
            "backend": "macos-window",
        },
    }
    source = f"TASK = {metadata!r}\ndef run(ctx): pass\n"
    task = parse_function_task_source(
        source, path=tmp_path / "sample.py", asset_root=tmp_path
    )
    assert task.target.backend == "macos-window"
    metadata["target"]["backend"] = "macos-widnow"
    with pytest.raises(ValueError, match="backend"):
        parse_function_task_source(
            f"TASK = {metadata!r}\ndef run(ctx): pass\n",
            path=tmp_path / "sample.py",
            asset_root=tmp_path,
        )


def test_native_details_use_window_rule_state_names(tmp_path):
    """原生脚本的就绪检查读取真实会话将使用的窗口配置。"""
    import json

    from game_automation.portable.application.local_control import (
        LocalControlApplication,
    )
    from game_automation.portable.application.task_catalog import TaskCatalog

    state_script = replace(
        script(), requires=TaskRequirements(states=("窗口专用状态",))
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "window-states.json").write_text(
        json.dumps({"groups": [{"state": "窗口专用状态"}]})
    )
    app = LocalControlApplication(
        catalog=TaskCatalog((state_script,)), project_root=tmp_path
    )
    details = app.describe_task("native")
    assert details.exit_code == 0
    assert details.readiness == (("状态: 窗口专用状态", "ok", "状态已配置"),)


def test_shared_resource_merge_preserves_native_target_through_control_entry(
    tmp_path, monkeypatch
):
    """补齐共享搜索后仍进入显式原生会话，不能丢失后端声明。"""
    from game_automation.portable.application import task_resources as script_resources
    from game_automation.portable.application.local_control import (
        LocalControlApplication,
    )
    from game_automation.portable.application.task_catalog import TaskCatalog
    from game_automation.portable.domain import (
        ImageMatch,
        ImageSearchSpec,
        ImageTemplate,
        TargetCatalog,
    )
    from game_automation.portable.domain.point_aliases import NamedImageSearch

    original = function_task(
        "native",
        'ctx.click_image("shared-search")',
        target=script().target,
        requires=TaskRequirements(searches=("shared-search",)),
    )
    shared = TargetCatalog(
        searches=(
            NamedImageSearch(
                "shared-search", ImageSearchSpec(ImageTemplate("unused.png"))
            ),
        )
    )
    monkeypatch.setattr(
        script_resources, "load_shared_task_resources", lambda root: shared
    )
    merged = script_resources.task_with_shared_resources(original, shared)
    assert merged.target is original.target

    class ImageFactory(Factory):
        @contextmanager
        def open(self, target, requirements, cancellation, logger):
            """返回原生设备和全局匹配位置。"""

            class Locator:
                def locate(self, template, **kwargs):
                    """模拟命中全局矩形。"""
                    return ImageMatch(Rect(100, 200, 10, 12), 1)

            try:
                yield RuntimePorts(
                    AreaWindow(Rect(100, 200, 80, 60)),
                    self.device,
                    image_locator=Locator(),
                )
            finally:
                self.closed = True

    factory = ImageFactory()
    app = LocalControlApplication(
        catalog=TaskCatalog((original,)),
        project_root=tmp_path,
        real_runtime_factory=factory,
    )
    assert app.run_named_task("native", dry_run=False).finish_reason == "completed"
    app.start_named_task("native", dry_run=False)
    assert app.wait_for_task_stop(2)
    assert app.current_task_run().finish_reason == "completed"
    assert factory.device.clicks == [Point(105, 206), Point(105, 206)]


@pytest.mark.parametrize("fail_close", (False, True))
def test_cancellation_arriving_during_close_wins_even_if_close_also_fails(fail_close):
    """停流期间用户取消不能被完成或清理失败覆盖。"""

    class Token:
        cancelled = False

        def is_cancelled(self):
            """返回可变取消状态。"""
            return self.cancelled

    token = Token()

    class ClosingFactory(Factory):
        @contextmanager
        def open(self, target, requirements, cancellation, logger):
            """在源关闭期间模拟到达的取消。"""
            try:
                yield RuntimePorts(AreaWindow(Rect(100, 200, 80, 60)), self.device)
            finally:
                token.cancelled = True
                self.closed = True
                if fail_close:
                    raise RuntimeError("stop failed")

    factory = ClosingFactory()
    result = run_task(
        script(),
        dry_run=False,
        real_runtime_factory=factory,
        cancellation_token=token,
    )
    assert result.finish_reason == "cancelled"
    assert result.exit_code == 130
    if fail_close:
        assert "cleanup failed" in result.error_message


def test_cli_plan_cannot_open_second_native_source_after_cleanup_failure(monkeypatch):
    """继续普通错误的计划也必须在源清理失败后停止。"""
    from game_automation.platform.local_desktop import composition
    from game_automation.platform.local_desktop.entrypoints import cli
    from game_automation.portable.application.run_plan import TaskPlanItem

    factories = []

    def build(workspace):
        """记录每个真实端口工厂，模拟关闭失败。"""
        factory = Factory(fail_close=True)
        factories.append(factory)
        return factory

    monkeypatch.setattr(composition, "build_native_runtime_factory", build)
    monkeypatch.setattr(
        cli,
        "_resolve_plan_items",
        lambda args: (
            TaskPlanItem("first", script()),
            TaskPlanItem("second", script()),
        ),
    )
    assert cli.main(["run-plan", "first", "second", "--continue-on-error"]) == 1
    assert len(factories) == 1
    assert factories[0].closed


def test_cli_native_details_use_window_rule_state_names(tmp_path):
    """CLI 的依赖检查与原生控制台及真正 reader 使用同一配置。"""
    import json

    from game_automation.platform.local_desktop.entrypoints import cli

    state_script = replace(
        script(), requires=TaskRequirements(states=("窗口专用状态",))
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "window-states.json").write_text(
        json.dumps({"groups": [{"state": "窗口专用状态"}]})
    )
    assert cli._describe_task(state_script, tmp_path).exit_code == 0


def test_background_backend_is_native_and_never_falls_through_to_desktop():
    """显式后台试验复用原生工厂，缺失时不能悄悄进入旧桌面输入。"""
    background = replace(
        script(), target=replace(script().target, backend="macos-window-background")
    )
    assert background.target.uses_native_window
    result = run_task(background, dry_run=False)
    assert result.finish_reason == "setup_failed"
    assert "desktop fallback is disabled" in result.error_message
    factory = Factory()
    result = run_task(background, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "completed"
    assert factory.device.clicks == [Point(105, 206)]


def test_background_cli_and_control_read_window_rules(tmp_path):
    """新试验后端的CLI和UI状态依赖都属于窗口规则。"""
    import json

    from game_automation.platform.local_desktop.entrypoints import cli
    from game_automation.portable.application.local_control import (
        LocalControlApplication,
    )
    from game_automation.portable.application.task_catalog import TaskCatalog

    background = replace(
        script(),
        target=replace(script().target, backend="macos-window-background"),
        requires=TaskRequirements(states=("窗口专用状态",)),
    )
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "window-states.json").write_text(
        json.dumps({"groups": [{"state": "窗口专用状态"}]})
    )
    app = LocalControlApplication(
        catalog=TaskCatalog((background,)), project_root=tmp_path
    )
    assert app.describe_task("native").exit_code == 0
    assert cli._describe_task(background, tmp_path).exit_code == 0


def test_native_runtime_control_drives_click_preparation_and_repeat_budget():
    """公开运行入口传递恢复边界和任务时钟，预算按有效时间结束。"""
    import pytest

    class Control:
        def __init__(self):
            """保存有效时间和已经执行的点击准备次数。"""
            self.now = 0.0
            self.preparations = 0

        def task_time(self):
            """提供平台定义的有效时间。"""
            return self.now

        def execute_input(self, action):
            """用公开输入边界包住定位和投递。"""
            self.preparations += 1
            return action()

    control = Control()

    class TimedFactory(Factory):
        @contextmanager
        def open(self, target, requirements, cancellation, logger):
            """将同一个时间源和输入边界交给运行入口。"""

            def wait(seconds):
                """只推进有效时间，避免测试依赖墙上时间。"""
                control.now += seconds

            self.device.wait = wait
            try:
                yield RuntimePorts(
                    AreaWindow(Rect(100, 200, 80, 60)), self.device, control=control
                )
            finally:
                self.closed = True

    factory = TimedFactory()
    timed = function_task(
        "native",
        "with ctx.deadline(0.1):\n"
        "    while True:\n"
        "        ctx.click(Point(5, 6))\n"
        "        ctx.wait(0.06)",
        target=script().target,
    )
    result = run_task(timed, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == "timed_out"
    assert factory.closed
    assert factory.device.clicks == [Point(105, 206), Point(105, 206)]
    assert control.preparations == 2
    assert control.now == pytest.approx(0.1)
