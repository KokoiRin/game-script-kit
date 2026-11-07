"""在已采集的Pillow图像上直接读取多点颜色，不截图、不做整图数组转换。

颜色规则来自portable值对象，输出沿用批量图像结果的计数与逻辑坐标。
"""
from math import floor, ceil
from game_automation.portable.domain import ImageBatchMatchResult, ImageMatch, Rect


def locate_color_pattern(screen, template, pattern):
    """共同平移整组点，全部RGB通道落入容差才命中。"""
    image = screen.image
    pixels = image.load()
    points = pattern.points
    radius = pattern.offset_radius
    offsets = [(dx,dy) for dy in range(-radius,radius+1) for dx in range(-radius,radius+1)]
    offsets.sort(key=lambda v: (abs(v[0])+abs(v[1]),v[1],v[0]))
    best_count, best_offset = -1, None
    for dx,dy in offsets:
        if any(not 0 <= p.x+dx < image.width or not 0 <= p.y+dy < image.height for p in points):
            continue
        count = sum(all(abs(actual-wanted) <= p.tolerance for actual,wanted in zip(pixels[p.x+dx,p.y+dy],p.rgb,strict=True)) for p in points)
        if count > best_count:
            best_count,best_offset = count,(dx,dy)
        if count == len(points):
            break
    count = max(0,best_count)
    rect = None
    if best_offset is not None:
        dx,dy = best_offset
        left = floor((min(p.x for p in points)+dx)/screen.pixels_per_point_x)
        top = floor((min(p.y for p in points)+dy)/screen.pixels_per_point_y)
        right = ceil((max(p.x for p in points)+dx+1)/screen.pixels_per_point_x)
        bottom = ceil((max(p.y for p in points)+dy+1)/screen.pixels_per_point_y)
        rect = Rect(left,top,right-left,bottom-top)
    match = ImageMatch(rect,1.0) if count == len(points) else None
    return ImageBatchMatchResult(template,match,0,best_confidence=count/len(points),best_rect=rect,
                                 matched_points=count,point_count=len(points))
