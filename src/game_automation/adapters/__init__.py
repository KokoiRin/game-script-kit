"""平台适配层 —— 实现 engine.ports 定义的端口协议。

实现关系：
  MacOSPointerDevice       → InputDevice
  DryRunInputDevice        → InputDevice
  PyAutoGuiPointerPositionReader → PointerPositionReader
  TerminalKeyStateReader   → KeyStateReader
"""
