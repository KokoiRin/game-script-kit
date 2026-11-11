"""验证显式原生后端的会话边界；不访问真实桌面。"""
from contextlib import contextmanager
from dataclasses import replace

from game_automation.portable.application.runtime_ports import RuntimePorts
from game_automation.portable.application.script_run import run_script
from game_automation.portable.domain import AreaWindow, Click, Point, Rect, Script
from game_automation.portable.domain.script import ScriptTarget


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
                raise RuntimeError('stream shutdown failed')


def script():
    """创建一个窗口局部点击脚本。"""
    return Script('native', AreaWindow(Rect(0, 0, 80, 60)), (Click(Point(5, 6)),), target=ScriptTarget('Example', 'Game', 80, 60, backend='macos-window'))


def test_explicit_native_backend_owns_all_ports():
    """原生后端只打开一次会话且只增加一次窗口原点。"""
    factory = Factory()
    result = run_script(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == 'completed'
    assert factory.closed
    assert factory.device.clicks == [Point(105, 206)]


def test_close_failure_never_reports_completed():
    """采集停止失败作为可见失败而非成功。"""
    factory = Factory(fail_close=True)
    result = run_script(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == 'cleanup_failed'
    assert result.exit_code == 1
    assert 'stream shutdown failed' in result.error_message


def test_native_does_not_fallback_to_global_backend():
    """缺少原生工厂必须失败，不访问旧设备。"""
    calls = []
    result = run_script(script(), dry_run=False, real_device_factory=lambda: calls.append(1))
    assert result.finish_reason == 'setup_failed'
    assert calls == []


def test_dry_run_does_not_open_native_session():
    """模拟模式保留无需平台依赖的执行路径。"""
    result = run_script(script(), dry_run=True)
    assert result.finish_reason == 'completed'


def test_native_window_override_is_rejected_before_open():
    """显式固定目标不能被入口参数悄悄改绑。"""
    factory = Factory()
    result = run_script(script(), dry_run=False, real_runtime_factory=factory, target_application='Other')
    assert result.finish_reason == 'configuration_failed'
    assert factory.closed is False


def test_cancelled_run_closes_and_preserves_cancellation_when_cleanup_fails():
    """取消是主结果，停流失败仍在错误信息中可见。"""
    from game_automation.portable.engine.runner import ScriptCancelledError
    factory = Factory(fail_close=True)
    def click(point):
        """模拟输入边界收到取消。"""
        raise ScriptCancelledError('cancelled by user')
    factory.device.click = click
    result = run_script(script(), dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == 'cancelled'
    assert result.exit_code == 130
    assert 'cleanup failed' in result.error_message
    assert factory.closed


def test_setup_failure_after_open_closes_runtime():
    """端口装配失败也必须释放已经打开的会话。"""
    from game_automation.portable.domain import Color, ColorIs, If
    factory = Factory()
    needs_color = replace(script(), steps=(If(ColorIs(Point(1, 1), Color(0, 0, 0)), (Click(Point(2, 2)),)),))
    result = run_script(needs_color, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == 'setup_failed'
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
    result = run_script(script(), dry_run=False, real_runtime_factory=Factory(fail_close=True), logger=logger, emit_step_events=True)
    terminal = [e for e in logger.events if e.event_type == 'run_finished']
    assert result.finish_reason == 'cleanup_failed'
    assert [e.status for e in terminal] == ['cleanup_failed']


def test_sync_and_background_control_use_same_runtime_factory(tmp_path):
    """控制应用的两个入口都注入同一种会话工厂。"""
    from game_automation.portable.application.local_control import LocalControlApplication
    from game_automation.portable.scripts_manager.catalog import ScriptCatalog
    factory = Factory()
    app = LocalControlApplication(catalog=ScriptCatalog((script(),)), project_root=tmp_path, real_runtime_factory=factory)
    assert app.run_named_script('native', dry_run=False).finish_reason == 'completed'
    app.start_named_script('native', dry_run=False)
    assert app.wait_for_script_stop(2)
    assert app.current_script_run().finish_reason == 'completed'
    assert factory.device.clicks == [Point(105, 206), Point(105, 206)]


def test_json_backend_opt_in_and_unknown_backend_fail(tmp_path):
    """旧声明默认桌面；原生选择必须显式且拒绝拼错。"""
    import json
    import pytest
    from game_automation.portable.application.config_script_loader import load_config_scripts
    data = {'name':'sample', 'steps':[{'wait':0}], 'target':{'application':'Example', 'window_title':'Game', 'width':80, 'height':60, 'backend':'macos-window'}}
    path = tmp_path / 'sample.json'
    path.write_text(json.dumps(data))
    assert load_config_scripts(tmp_path, asset_root=tmp_path)[0].target.backend == 'macos-window'
    data['target']['backend'] = 'macos-widnow'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='backend'):
        load_config_scripts(tmp_path, asset_root=tmp_path)


def test_native_details_use_window_rule_state_names(tmp_path):
    """原生脚本的就绪检查读取真实会话将使用的窗口配置。"""
    import json
    from game_automation.portable.application.local_control import LocalControlApplication
    from game_automation.portable.domain import If, ScreenStateIs
    from game_automation.portable.scripts_manager.catalog import ScriptCatalog
    state_script = replace(script(), steps=(If(ScreenStateIs('窗口专用状态'), (Click(Point(1, 1)),)),))
    assets = tmp_path / 'assets'
    assets.mkdir()
    (assets / 'window-states.json').write_text(json.dumps({'groups':[{'state':'窗口专用状态'}]}))
    (assets / 'screen-states.json').write_text(json.dumps({'groups':[{'state':'旧桌面状态'}]}))
    app = LocalControlApplication(catalog=ScriptCatalog((state_script,)), project_root=tmp_path)
    details = app.describe_script('native')
    assert details.exit_code == 0
    assert details.readiness == (('状态: 窗口专用状态', 'ok', '状态已配置'),)


def test_shared_resource_merge_preserves_native_target_through_control_entry(tmp_path, monkeypatch):
    """补齐共享搜索后仍进入显式原生会话，不能丢失后端声明。"""
    from game_automation.portable.application import script_resources
    from game_automation.portable.application.local_control import LocalControlApplication
    from game_automation.portable.domain import ImageMatch, ImageSearchSpec, ImageTarget, ImageTemplate, SearchRef, TargetCatalog
    from game_automation.portable.domain.point_aliases import NamedImageSearch
    from game_automation.portable.scripts_manager.catalog import ScriptCatalog
    original = replace(script(), steps=(Click(ImageTarget(SearchRef('shared-search'))),))
    shared = TargetCatalog(searches=(NamedImageSearch('shared-search', ImageSearchSpec(ImageTemplate('unused.png'))),))
    monkeypatch.setattr(script_resources, 'load_shared_script_resources', lambda root: shared)
    merged = script_resources.script_with_shared_resources(original, shared)
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
                yield RuntimePorts(AreaWindow(Rect(100, 200, 80, 60)), self.device, image_locator=Locator())
            finally:
                self.closed = True
    factory = ImageFactory()
    app = LocalControlApplication(catalog=ScriptCatalog((original,)), project_root=tmp_path, real_runtime_factory=factory)
    assert app.run_named_script('native', dry_run=False).finish_reason == 'completed'
    app.start_named_script('native', dry_run=False)
    assert app.wait_for_script_stop(2)
    assert app.current_script_run().finish_reason == 'completed'
    assert factory.device.clicks == [Point(105, 206), Point(105, 206)]


def test_cancellation_arriving_during_close_wins_even_if_close_also_fails():
    """停流期间用户取消不能被完成或清理失败覆盖。"""
    for fail_close in (False, True):
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
                        raise RuntimeError('stop failed')
        factory = ClosingFactory()
        result = run_script(script(), dry_run=False, real_runtime_factory=factory, cancellation_token=token)
        assert result.finish_reason == 'cancelled'
        assert result.exit_code == 130
        if fail_close:
            assert 'cleanup failed' in result.error_message


def test_cli_plan_cannot_open_second_native_source_after_cleanup_failure(monkeypatch):
    """继续普通错误的计划也必须在源清理失败后停止。"""
    from game_automation.platform.local_desktop import composition
    from game_automation.platform.local_desktop.entrypoints import cli
    from game_automation.portable.application.run_plan import ScriptPlanItem
    factories = []
    def build(workspace):
        """记录每个真实端口工厂，模拟关闭失败。"""
        factory = Factory(fail_close=True)
        factories.append(factory)
        return factory
    monkeypatch.setattr(composition, 'build_native_runtime_factory', build)
    monkeypatch.setattr(cli, '_resolve_plan_items', lambda args: (ScriptPlanItem('first', script()), ScriptPlanItem('second', script())))
    assert cli.main(['run-plan', 'first', 'second', '--continue-on-error']) == 1
    assert len(factories) == 1
    assert factories[0].closed


def test_cli_native_details_use_window_rule_state_names(tmp_path):
    """CLI 的依赖检查与原生控制台及真正 reader 使用同一配置。"""
    import json
    from game_automation.platform.local_desktop.entrypoints import cli
    from game_automation.portable.domain import If, ScreenStateIs
    state_script = replace(script(), steps=(If(ScreenStateIs('窗口专用状态'), (Click(Point(1, 1)),)),))
    assets = tmp_path / 'assets'
    assets.mkdir()
    (assets / 'window-states.json').write_text(json.dumps({'groups':[{'state':'窗口专用状态'}]}))
    (assets / 'screen-states.json').write_text(json.dumps({'groups':[{'state':'旧桌面状态'}]}))
    assert cli._describe_script(state_script, tmp_path).exit_code == 0


def test_background_backend_is_native_and_never_falls_through_to_desktop():
    """显式后台试验复用原生工厂，缺失时不能悄悄进入旧桌面输入。"""
    background = replace(script(), target=replace(script().target, backend='macos-window-background'))
    assert background.target.uses_native_window
    calls = []
    result = run_script(background, dry_run=False, real_device_factory=lambda: calls.append('desktop'))
    assert result.finish_reason == 'setup_failed'
    assert calls == []
    factory = Factory()
    result = run_script(background, dry_run=False, real_runtime_factory=factory)
    assert result.finish_reason == 'completed'
    assert factory.device.clicks == [Point(105, 206)]


def test_background_cli_and_control_read_window_rules(tmp_path):
    """新试验后端的CLI和UI状态依赖都属于窗口规则。"""
    import json
    from game_automation.platform.local_desktop.entrypoints import cli
    from game_automation.portable.application.local_control import LocalControlApplication
    from game_automation.portable.domain import If, ScreenStateIs
    from game_automation.portable.scripts_manager.catalog import ScriptCatalog
    background = replace(script(), target=replace(script().target, backend='macos-window-background'),
                         steps=(If(ScreenStateIs('窗口专用状态'), (Click(Point(1, 1)),)),))
    assets = tmp_path / 'assets'
    assets.mkdir()
    (assets / 'window-states.json').write_text(json.dumps({'groups':[{'state':'窗口专用状态'}]}))
    (assets / 'screen-states.json').write_text(json.dumps({'groups':[{'state':'旧桌面状态'}]}))
    app = LocalControlApplication(catalog=ScriptCatalog((background,)), project_root=tmp_path)
    assert app.describe_script('native').exit_code == 0
    assert cli._describe_script(background, tmp_path).exit_code == 0
