"""独立视觉自动化靶场 package。

本 package 提供可见目标应用和外部真值接口；它不导入或执行 Star 自动化核心。
"""

from star_visual_lab.scenario import (
    ScenarioActionError,
    ScenarioEvent,
    ScenarioSnapshot,
    TaskFlowScenario,
)

__all__ = [
    "ScenarioActionError",
    "ScenarioEvent",
    "ScenarioSnapshot",
    "TaskFlowScenario",
]
