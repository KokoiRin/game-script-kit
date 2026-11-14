"""导出函数任务的名称索引。

任务文件由应用层从所选工作区发现，本模块只提供无副作用的 catalog。
"""

from game_automation.portable.scripts_manager.catalog import (
    ScriptCatalog,
    ScriptNotFoundError,
)

__all__ = ["ScriptCatalog", "ScriptNotFoundError"]
