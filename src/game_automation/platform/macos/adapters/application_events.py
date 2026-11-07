"""为无 GUI 的 macOS 后台处理应用状态通知。

本 module 在平台协议主线程中短暂推进系统运行循环，使 NSWorkspace 的
运行应用快照更新；不查询窗口、不激活应用、不执行输入或申请权限。
"""


def process_application_events() -> None:
    """在主线程处理待到达的系统事件，避免运行应用列表停在旧快照。"""
    from CoreFoundation import CFRunLoopRunInMode, kCFRunLoopDefaultMode

    # NSWorkspace 只在主运行循环的常用模式中更新；单纯重复读取属性不会刷新。
    # 在请求到达后处理事件，覆盖后台阻塞等待输入期间发生的应用启动与退出。
    CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.01, False)
