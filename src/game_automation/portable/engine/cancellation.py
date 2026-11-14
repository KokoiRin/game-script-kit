"""声明任务终止取消及平台端口使用的取消异常。

本模块只保存异常类型，不启动运行器或平台能力。直接任务的取消穿过普通
异常恢复逻辑，运行上下文在平台调用边界转换取消信号。
"""


class ScriptCancelledError(RuntimeError):
    """表示平台运行被外部取消信号停止。"""


class RunCancelled(BaseException):
    """让终止取消穿过任务的普通异常恢复逻辑。"""
