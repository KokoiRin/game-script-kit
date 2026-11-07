"""查询和申请当前 macOS 后台进程的桌面权限。

本 module 仅连接 Accessibility 与屏幕捕获权限 API；不读取窗口、截图、
执行脚本或代替用户授权。桌面协议延迟创建它，查询永不触发申请弹窗。
"""


class MacOSDesktopPermissions:
    def __init__(self, *, accessibility=None, quartz=None) -> None:
        """注入系统权限接口，只有实际查询时才加载 macOS 框架。"""
        self._accessibility = accessibility
        self._quartz = quartz

    def _frameworks(self):
        """延迟取得两个系统框架，保持普通后台启动无权限副作用。"""
        if self._accessibility is None:
            import ApplicationServices
            self._accessibility = ApplicationServices
        if self._quartz is None:
            import Quartz
            self._quartz = Quartz
        return self._accessibility, self._quartz

    def status(self) -> dict[str, bool]:
        """只检查实际执行进程的权限，不以壳进程的授权状态代替后台。"""
        accessibility, quartz = self._frameworks()
        return {
            'accessibility': bool(accessibility.AXIsProcessTrusted()),
            'screen_recording': bool(quartz.CGPreflightScreenCaptureAccess()),
        }

    def request(self, kind: str) -> dict[str, bool]:
        """只申请用户选中的权限，异步提示后仍以系统查询结果为准。"""
        if kind not in {'accessibility', 'screen_recording'}:
            raise ValueError(f'unknown desktop permission: {kind}')
        accessibility, quartz = self._frameworks()
        if kind == 'accessibility':
            accessibility.AXIsProcessTrustedWithOptions({accessibility.kAXTrustedCheckOptionPrompt: True})
        else:
            quartz.CGRequestScreenCaptureAccess()
        return self.status()
