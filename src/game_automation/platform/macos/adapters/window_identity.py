"""把已选AX窗口绑定到唯一CG编号并核对身份，不采集画面或激活窗口。

请求式截图与持续窗口流共用本边界，调用方分别拥有自己的图像资源。
"""

from game_automation.portable.application.capture_errors import WindowCaptureError


class BoundWindow:
    """固定窗口编号和标题，允许移动但拒绝替换与尺寸变化。"""

    def __init__(self, window, *, quartz=None):
        """按进程和唯一完整几何首次绑定，不用AX标题猜测。"""
        if quartz is None:
            import Quartz
            quartz = Quartz
        self.quartz = quartz
        self.window = window
        self.number = None
        self.title = None
        self.check()

    def check(self):
        """每次仅核对固定编号、进程、标题及原始逻辑尺寸。"""
        q = self.quartz
        pid = int(self.window.id.split(':', 1)[0])
        rows = q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionOnScreenOnly | q.kCGWindowListExcludeDesktopElements,
                                          q.kCGNullWindowID) or ()
        candidates = [item for item in rows if item.get(q.kCGWindowOwnerPID) == pid
                      and item.get(q.kCGWindowLayer) == 0]
        if self.number is None:
            rect = self.window.rect
            expected = (rect.left, rect.top, rect.width, rect.height)
            candidates = [item for item in candidates if logical_bounds(item.get(q.kCGWindowBounds, {})) == expected]
        else:
            candidates = [item for item in candidates if item.get(q.kCGWindowNumber) == self.number
                          and item.get(q.kCGWindowName) == self.title]
        if len(candidates) != 1:
            raise WindowCaptureError('目标窗口已关闭、不可见、标题已变化或几何不唯一，请停止观察并重新选择窗口')
        item = candidates[0]
        bounds = logical_bounds(item.get(q.kCGWindowBounds, {}))
        if bounds is None or bounds[2:] != (self.window.rect.width, self.window.rect.height):
            raise WindowCaptureError('目标窗口尺寸已变化，请恢复采集素材时的窗口尺寸')
        if self.number is None:
            number = item.get(q.kCGWindowNumber)
            if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
                raise WindowCaptureError('目标窗口缺少有效编号，请重新选择窗口')
            self.number, self.title = number, item.get(q.kCGWindowName)
        return item


def logical_bounds(bounds):
    """归一化系统完整窗口几何，拒绝缺失和非有限值。"""
    try:
        return tuple(round(bounds[key]) for key in ('X', 'Y', 'Width', 'Height'))
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
