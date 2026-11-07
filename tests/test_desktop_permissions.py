"""验证桌面权限查询与申请边界。

本 module 通过系统框架替身检查无弹窗查询、按需申请及协议映射，
不修改当前机器授权，也不读取真实窗口或屏幕。
"""

from types import SimpleNamespace

import pytest

from game_automation.platform.macos.adapters.desktop_permissions import MacOSDesktopPermissions
from game_automation.platform.local_desktop.entrypoints.desktop_backend import DesktopBackend


@pytest.fixture
def permissions():
    """记录权限系统调用，模拟尚未授权且申请尚未完成的状态。"""
    calls = []
    ax = SimpleNamespace(
        AXIsProcessTrusted=lambda: False,
        kAXTrustedCheckOptionPrompt='prompt',
        AXIsProcessTrustedWithOptions=lambda options: calls.append(('accessibility', options)) or False,
    )
    quartz = SimpleNamespace(
        CGPreflightScreenCaptureAccess=lambda: True,
        CGRequestScreenCaptureAccess=lambda: calls.append(('screen_recording',)) or False,
    )
    return MacOSDesktopPermissions(accessibility=ax, quartz=quartz), calls


def test_permission_status_never_prompts(permissions):
    """状态读取只查询系统，不因打开控制台主动申请权限。"""
    service, calls = permissions
    assert service.status() == {'accessibility': False, 'screen_recording': True}
    assert calls == []


def test_accessibility_request_does_not_claim_async_grant(permissions):
    """辅助功能提示是异步的，发起申请不等于已经授权。"""
    service, calls = permissions
    assert service.request('accessibility')['accessibility'] is False
    assert calls == [('accessibility', {'prompt': True})]


def test_capture_request_never_requests_window_control(permissions):
    """截图权限申请不隐式申请辅助功能权限。"""
    service, calls = permissions
    service.request('screen_recording')
    assert calls == [('screen_recording',)]


def test_invalid_permission_has_no_system_side_effect(permissions):
    """未知权限在调用系统前明确拒绝。"""
    service, calls = permissions
    with pytest.raises(ValueError, match='permission'):
        service.request('disk')
    assert calls == []


def test_backend_permissions_do_not_load_scripts_or_preparation(tmp_path, permissions):
    """后台权限请求独立于素材采集和脚本目录加载。"""
    service, calls = permissions
    def forbidden():
        """禁止权限查询创建运行服务。"""
        pytest.fail('must not load script catalog')
    session = DesktopBackend(tmp_path, preparation=object(), control_factory=forbidden, permissions=service)
    try:
        assert session.dispatch('permissions.status', {}) == {'accessibility': False, 'screen_recording': True}
        assert calls == []
        result = session.dispatch('permissions.request', {'kind': 'accessibility'})
        assert result['accessibility'] is False
        assert len(calls) == 1
        with pytest.raises(ValueError):
            session.dispatch('permissions.request', {'kind': ''})
    finally:
        session.close()


def test_permission_request_is_rejected_during_script_run(tmp_path, permissions):
    """运行中不能弹出权限申请干扰目标应用，状态查询仍可使用。"""
    service, calls = permissions
    class Control:
        def list_scripts(self):
            """提供最小脚本查询接口以正常加载控制服务。"""
            return ()
        def list_script_config_errors(self):
            """提供无配置错误的控制服务。"""
            return ()
        def current_script_run(self):
            """模拟运行中的公开会话状态。"""
            return SimpleNamespace(running=True)
        def stop_running_script(self):
            """接受会话关闭请求而不访问设备。"""
        def wait_for_script_stop(self, timeout):
            """模拟关闭时已回收线程。"""
            return True
    session = DesktopBackend(tmp_path, preparation=object(), control_factory=Control, permissions=service)
    try:
        session.dispatch('script.list', {})
        with pytest.raises(RuntimeError, match='running'):
            session.dispatch('permissions.request', {'kind': 'accessibility'})
        assert session.dispatch('permissions.status', {})['screen_recording'] is True
        assert calls == []
    finally:
        session.close()
