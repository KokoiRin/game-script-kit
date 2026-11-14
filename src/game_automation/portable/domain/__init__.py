"""聚合导出纯领域数据模型。

本 module 只提供领域类型的便捷 import surface；它不执行脚本、不访问平台 adapter，
也不承载应用编排逻辑。
"""

from game_automation.portable.domain.color import Color
from game_automation.portable.domain.geometry import Point, Rect
from game_automation.portable.domain.image_matching import (
    ImageBatchMatchResult,
    ImageLookupResult,
    ImageMatch,
    ImageSearchRequest,
    ImageTemplate,
)
from game_automation.portable.domain.point_aliases import (
    ImageRef,
    ImageSearchSpec,
    NamedImage,
    NamedImageSearch,
    NamedPoint,
    NamedRegion,
    PointRef,
    RegionRef,
    SearchRef,
    TargetCatalog,
    UnknownImageNameError,
    UnknownImageSearchNameError,
    UnknownPointNameError,
    UnknownRegionNameError,
)
from game_automation.portable.domain.screen_state import (
    UNKNOWN_SCREEN_STATE,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)
from game_automation.portable.domain.target_offsets import OffsetTarget
from game_automation.portable.domain.targets import ImageTarget
from game_automation.portable.domain.task import (
    FunctionTask,
    ScriptTarget,
    TaskRequirements,
)
from game_automation.portable.domain.windows import AreaWindow, ScreenWindow, Window

__all__ = [
    "AreaWindow",
    "FunctionTask",
    "ScriptTarget",
    "TaskRequirements",
    "Color",
    "ImageBatchMatchResult",
    "ImageLookupResult",
    "ImageMatch",
    "ImageRef",
    "ImageSearchSpec",
    "ImageSearchRequest",
    "ImageTemplate",
    "ImageTarget",
    "NamedImage",
    "NamedImageSearch",
    "NamedPoint",
    "NamedRegion",
    "OffsetTarget",
    "Point",
    "PointRef",
    "Rect",
    "ScreenWindow",
    "ScreenStateCandidate",
    "ScreenStateCandidateResult",
    "ScreenStateProbeResult",
    "RegionRef",
    "SearchRef",
    "TargetCatalog",
    "UNKNOWN_SCREEN_STATE",
    "UnknownImageNameError",
    "UnknownImageSearchNameError",
    "UnknownPointNameError",
    "UnknownRegionNameError",
    "Window",
]
