"""游戏自动化框架的顶层 package。

本 package 只暴露项目级元信息，并把代码分成 portable 与 platform 两大区域；
portable 承载可迁移核心，platform 承载当前桌面平台入口和 I/O adapter。
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
