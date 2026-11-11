"""声明可跨捕获和输入边界传播的协作取消信号。

本模块只保存异常类型，不装配或启动执行器；准备 adapter 导入它不会加载脚本运行服务。
runner 保留同名导出，以兼容已有调用方。
"""


class ScriptCancelledError(RuntimeError):
    """表示脚本运行被外部取消信号停止。"""
