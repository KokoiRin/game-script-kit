"""游戏自动化框架的顶层 package。

本 package 只暴露项目级元信息，并承载 domain、engine、application、adapters
等下级 modules；它不放置运行编排、平台适配或脚本定义。
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
