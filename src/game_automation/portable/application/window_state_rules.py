"""管理按窗口相对坐标配置的实时识别素材。

本 module 复用现有状态配置解析器，并保存冻结帧裁图与状态关联；
不采集桌面、不执行动作，也不更改旧 screen-states.json 的屏幕坐标语义。
"""

import json
import math
import tempfile
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.project_assets import IMAGE_ASSET_SUFFIXES
from game_automation.portable.application.screen_state_config import (
    load_screen_state_candidates,
)
from game_automation.portable.domain import Rect, ScreenStateCandidate
from game_automation.portable.domain.color_pattern import ColorPattern, ColorPoint


@dataclass(frozen=True, slots=True)
class WindowStateRules:
    """将已验证的候选素材绑定到采集时的窗口逻辑尺寸。"""

    candidates: tuple[ScreenStateCandidate, ...]
    width: int
    height: int
    pixel_width: int | None = None
    pixel_height: int | None = None
    priorities: tuple[int, ...] = ()
    patterns: tuple[ColorPattern | None, ...] = ()

    def __post_init__(self) -> None:
        """旧构造默认同层，显式优先级必须逐候选对齐。"""
        if not self.priorities:
            object.__setattr__(self, "priorities", (0,) * len(self.candidates))
        if len(self.priorities) != len(self.candidates) or any(
            type(p) is not int for p in self.priorities
        ):
            raise ValueError("窗口状态优先级必须是逐候选对齐的整数")
        if not self.patterns:
            object.__setattr__(self, "patterns", (None,) * len(self.candidates))
        if len(self.patterns) != len(self.candidates):
            raise ValueError("窗口多点特征必须逐候选对齐")
        for pattern in self.patterns:
            if pattern is not None:
                if not isinstance(pattern, ColorPattern):
                    raise ValueError("窗口多点特征类型无效")
                if any(
                    p.x >= (self.pixel_width or 0) or p.y >= (self.pixel_height or 0)
                    for p in pattern.points
                ):
                    raise ValueError("多点坐标超出采集截图像素尺寸")


def rules_path(workspace: Path) -> Path:
    """返回独立的窗口识别配置，避免改变原有脚本状态配置的坐标含义。"""
    assets = (workspace / "assets").resolve()
    if not assets.is_relative_to(workspace.resolve()):
        raise ValueError("素材目录必须位于当前工作区内")
    path = assets / "window-states.json"
    if path.is_symlink():
        raise ValueError("状态配置不能是符号链接")
    return path


def load_window_state_rules(workspace: Path) -> WindowStateRules:
    """加载已有状态规则，缺失或损坏时提供明确的配置错误。"""
    path = rules_path(workspace)
    if not path.exists():
        raise ValueError("还没有实时状态素材，请先在素材准备页框选并保存状态素材")
    data = json.loads(path.read_text())
    size = data.get("window_size", {})
    width, height = size.get("width"), size.get("height")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("状态素材缺少有效的采集窗口尺寸")
    candidates = load_screen_state_candidates(
        path, asset_root=path.parent, supported_suffixes=IMAGE_ASSET_SUFFIXES
    )
    pixels = data.get("pixel_size", {})
    pw, ph = pixels.get("width"), pixels.get("height")
    if type(pw) is not int or type(ph) is not int or pw <= 0 or ph <= 0:
        raise ValueError("状态素材缺少截图像素尺寸，请重新采集素材")
    priorities = []
    patterns = []
    states = {}
    for group in data["groups"]:
        priority = _priority(group.get("priority", 0))
        state = group["state"]
        if state in states and states[state] != priority:
            raise ValueError("同一状态不能配置冲突的优先级")
        states[state] = priority
        priorities.extend([priority] * len(group["searches"]))
        patterns.extend(_color_pattern(search) for search in group["searches"])
    return WindowStateRules(
        candidates, width, height, pw, ph, tuple(priorities), tuple(patterns)
    )


def list_window_state_rules(workspace: Path) -> dict:
    """列出状态与搜索区域，尚未创建配置时返回空集合。"""
    if not rules_path(workspace).exists():
        return {"rules": []}
    rules = load_window_state_rules(workspace)
    return {
        "rules": [
            {
                "state": c.name,
                "name": c.search_name,
                "image": Path(c.template.path).name,
                "min_confidence": c.search.min_confidence,
                "priority": priority,
                "method": "template" if pattern is None else "points",
                "point_count": None if pattern is None else len(pattern.points),
                "offset_radius": None if pattern is None else pattern.offset_radius,
                "region": None
                if c.search.region is None
                else rect_dict(c.search.region),
            }
            for c, priority, pattern in zip(
                rules.candidates, rules.priorities, rules.patterns, strict=True
            )
        ]
    }


def save_window_state_rule(
    workspace: Path,
    preparation,
    *,
    frame_id: str,
    crop: Rect,
    name: str,
    state: str,
    min_confidence: float = 0.9,
    search_region: Rect | None = None,
    priority: int | None = None,
) -> dict:
    """校验冻结帧、搜索范围与配置后，保存模板并原子登记状态。"""
    if not isinstance(state, str) or not state.strip() or len(state.strip()) > 80:
        raise ValueError("状态名称必须为 1 到 80 个字符")
    if (
        isinstance(min_confidence, bool)
        or not math.isfinite(min_confidence)
        or not 0 < min_confidence <= 1
    ):
        raise ValueError("匹配阈值必须大于 0 且不超过 1")
    if priority is not None:
        _priority(priority)
    frame = preparation.current_frame(frame_id)
    for region in (crop, search_region):
        if region is not None and (
            region.left < 0
            or region.top < 0
            or region.left + region.width > frame.image.width
            or region.top + region.height > frame.image.height
        ):
            raise ValueError("框选区域超出当前截图")
    if search_region is not None and not (
        search_region.left <= crop.left
        and search_region.top <= crop.top
        and search_region.left + search_region.width >= crop.left + crop.width
        and search_region.top + search_region.height >= crop.top + crop.height
    ):
        raise ValueError("搜索范围必须包含素材的裁剪位置")
    path = rules_path(workspace)
    size = {"width": frame.window.rect.width, "height": frame.window.rect.height}
    pixels = {"width": frame.image.width, "height": frame.image.height}
    data = {"window_size": size, "pixel_size": pixels, "groups": []}
    if path.exists():
        load_window_state_rules(workspace)
        data = json.loads(path.read_text())
        if data["window_size"] != size or data["pixel_size"] != pixels:
            raise ValueError("当前窗口尺寸与已有素材不同，请恢复原窗口尺寸后采集")
    matching_groups = [g for g in data["groups"] if g["state"] == state.strip()]
    if priority is not None:
        for existing_group in matching_groups:
            existing_group["priority"] = priority
    logical = None
    if search_region is not None:
        left = math.floor(search_region.left * size["width"] / frame.image.width)
        top = math.floor(search_region.top * size["height"] / frame.image.height)
        right = math.ceil(
            (search_region.left + search_region.width)
            * size["width"]
            / frame.image.width
        )
        bottom = math.ceil(
            (search_region.top + search_region.height)
            * size["height"]
            / frame.image.height
        )
        logical = {
            "left": left,
            "top": top,
            "width": right - left,
            "height": bottom - top,
        }
    image = preparation.save_crop(frame_id, crop, name)
    item = {"name": name, "image": image, "min_confidence": min_confidence}
    if logical is not None:
        item["region"] = logical
    group = next((g for g in data["groups"] if g["state"] == state.strip()), None)
    if group is None:
        group = {
            "state": state.strip(),
            "searches": [],
            "priority": 0 if priority is None else priority,
        }
        data["groups"].append(group)
    group["searches"].append(item)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=path.parent,
            prefix=".window-states-",
            suffix=".json",
            encoding="utf-8",
            delete=False,
        ) as output:
            temporary = Path(output.name)
            json.dump(data, output, ensure_ascii=False, indent=2)
            output.write("\n")
        temporary.replace(path)
    except BaseException:
        (path.parent / image).unlink(missing_ok=True)
        raise
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "image": image,
        "state": state.strip(),
        **list_window_state_rules(workspace),
    }


def rect_dict(rect: Rect) -> dict:
    """把已解析矩形转换成用户可查看的窗口相对区域。"""
    return {
        "left": rect.left,
        "top": rect.top,
        "width": rect.width,
        "height": rect.height,
    }


def _priority(value) -> int:
    """优先级仅接受整数，不隐式转换布尔、字符串或小数。"""
    if type(value) is not int:
        raise ValueError("窗口状态优先级必须是整数")
    return value


def _color_pattern(search) -> ColorPattern | None:
    """解析窗口专用多点方法，坏配置明确失败而不退回模板。"""
    method = search.get("method", "template")
    if method == "template":
        if "points" in search or "offset_radius" in search:
            raise ValueError("多点配置必须明确设置method为points")
        return None
    if method != "points":
        raise ValueError("窗口识别method必须是template或points")
    values = search.get("points")
    if not isinstance(values, list):
        raise ValueError("多点特征points必须是数组")
    points = []
    for item in values:
        if (
            not isinstance(item, dict)
            or not all(k in item for k in ("x", "y", "rgb"))
            or not isinstance(item["rgb"], list)
        ):
            raise ValueError("多点特征必须包含x、y和RGB数组")
        points.append(
            ColorPoint(
                item["x"], item["y"], tuple(item["rgb"]), item.get("tolerance", 35)
            )
        )
    return ColorPattern(tuple(points), search.get("offset_radius", 1))
