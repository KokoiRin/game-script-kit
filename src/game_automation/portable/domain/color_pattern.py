"""定义固定像素多点颜色特征及容差，不读取图片或操作设备。

窗口配置负责坐标与采集尺寸校验，桌面 adapter 在同一帧中执行整组偏移匹配。
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ColorPoint:
    """保存截图内一个固定位置及逐RGB通道允许的误差。"""

    x: int
    y: int
    rgb: tuple[int, int, int]
    tolerance: int = 35

    def __post_init__(self):
        """拒绝布尔、越界颜色及无界容差，不隐式截断小数。"""
        if any(type(v) is not int or v < 0 for v in (self.x, self.y)):
            raise ValueError("多点坐标必须是非负整数像素")
        if (
            not isinstance(self.rgb, tuple)
            or len(self.rgb) != 3
            or any(type(v) is not int or not 0 <= v <= 255 for v in self.rgb)
        ):
            raise ValueError("多点RGB必须是三个0到255的整数")
        if type(self.tolerance) is not int or not 0 <= self.tolerance <= 100:
            raise ValueError("多点颜色容差必须是0到100的整数")


@dataclass(frozen=True, slots=True)
class ColorPattern:
    """一组所有点都需满足的颜色特征，允许有界共同平移。"""

    points: tuple[ColorPoint, ...]
    offset_radius: int = 1

    def __post_init__(self):
        """限制点数和搜索偏移，拒绝重复位置造成的虚假证据。"""
        if (
            not isinstance(self.points, tuple)
            or not 2 <= len(self.points) <= 64
            or not all(isinstance(p, ColorPoint) for p in self.points)
        ):
            raise ValueError("多点特征必须包含2到64个颜色点")
        if len({(p.x, p.y) for p in self.points}) != len(self.points):
            raise ValueError("多点特征不能包含重复坐标")
        if type(self.offset_radius) is not int or not 0 <= self.offset_radius <= 2:
            raise ValueError("多点整体偏移必须是0到2的整数像素")


def validate_point_evidence(
    point_count, matched_points, *, skipped: bool, found: bool
) -> None:
    """约束模板无点数、多点全点命中及跳过无检查证据。"""
    if point_count is None:
        if matched_points is not None:
            raise ValueError("模板结果不能包含多点计数")
        return
    if type(point_count) is not int or not 2 <= point_count <= 64:
        raise ValueError("多点结果总数必须为2到64的整数")
    if skipped:
        if matched_points is not None:
            raise ValueError("跳过的多点结果不能包含匹配点数")
        return
    if type(matched_points) is not int or not 0 <= matched_points <= point_count:
        raise ValueError("多点结果匹配数必须为0到总数的整数")
    if found != (matched_points == point_count):
        raise ValueError("多点结果必须全部点通过才命中")
