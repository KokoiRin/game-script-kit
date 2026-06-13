"""平台 adapter package，实现 engine.ports 定义的端口协议。

本 package 只承载具体 I/O adapter；它不包含领域模型、不解释脚本，
也不决定一次脚本运行应该选择哪些 adapter。

实现关系：
  MacOSPointerDevice       → InputDevice
  DryRunInputDevice        → InputDevice
  PyAutoGuiPointerPositionReader → PointerPositionReader
  TerminalKeyStateReader   → KeyStateReader
"""
