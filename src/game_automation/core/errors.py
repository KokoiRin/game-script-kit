"""定义设备 adapter 相关的异常类型。"""


class AdapterSetupError(RuntimeError):
    """表示 adapter 的依赖、权限或运行环境尚未准备好。"""


class AdapterUnsupportedError(AdapterSetupError):
    """表示当前平台不支持所选择的 adapter。"""
