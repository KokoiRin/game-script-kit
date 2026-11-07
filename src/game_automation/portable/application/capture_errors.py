"""声明穿过图像匹配边界的采集诊断。

此 module 不捕获画面；平台提供中文原因，匹配器原样传播给调用者。
"""


class WindowCaptureError(RuntimeError):
    """标记可直接展示的窗口身份、权限或截图几何错误。"""
