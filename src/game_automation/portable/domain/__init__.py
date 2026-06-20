"""聚合导出纯领域数据模型。

本 module 只提供领域类型的便捷 import surface；它不执行脚本、不访问平台 adapter，
也不承载应用编排逻辑。
"""

from game_automation.portable.domain.actions import Click, ClickTarget, Drag, If, PrimitiveAction, Repeat, Step, Wait, WaitUntil
from game_automation.portable.domain.color import Color
from game_automation.portable.domain.conditions import ColorIs, Condition, ImageExists
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
from game_automation.portable.domain.script import Script
from game_automation.portable.domain.screen_state import (
    UNKNOWN_SCREEN_STATE,
    ScreenStateCandidate,
    ScreenStateCandidateResult,
    ScreenStateProbeResult,
)
from game_automation.portable.domain.target_offsets import OffsetTarget
from game_automation.portable.domain.targets import ImageTarget
from game_automation.portable.domain.windows import AreaWindow, ScreenWindow, Window

__all__ = [
    "AreaWindow",
    "Click",
    "ClickTarget",
    "Color",
    "ColorIs",
    "Condition",
    "Drag",
    "If",
    "ImageExists",
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
    "PrimitiveAction",
    "Rect",
    "Repeat",
    "ScreenWindow",
    "ScreenStateCandidate",
    "ScreenStateCandidateResult",
    "ScreenStateProbeResult",
    "RegionRef",
    "SearchRef",
    "Script",
    "Step",
    "TargetCatalog",
    "UNKNOWN_SCREEN_STATE",
    "UnknownImageNameError",
    "UnknownImageSearchNameError",
    "UnknownPointNameError",
    "UnknownRegionNameError",
    "Wait",
    "WaitUntil",
    "Window",
]
