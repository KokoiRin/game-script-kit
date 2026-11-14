"""把统一窗口图像源适配为全局逻辑坐标的取色与图像端口。

识图算法和状态优先级复用既有实现；本模块只转换边界坐标，不拥有或关闭图像源。
"""

from dataclasses import replace

from game_automation.platform.desktop.adapters.image_matching import (
    PyAutoGuiScreenImageLocator,
)
from game_automation.platform.macos.adapters.window_state_probe import (
    MacOSWindowStateProbe,
)
from game_automation.portable.domain import Color, ImageSearchRequest, Rect


class WindowColorReader:
    def __init__(self, session):
        """保存非拥有的会话引用。"""
        self.session = session

    def read_color(self, point):
        """将全局逻辑点映射为窗口内原始像素点。"""
        self.session.validate_point(point)
        r = self.session.window.rect
        with self.session.screenshot() as image:
            x = int((point.x - r.left) * image.width / r.width)
            y = int((point.y - r.top) * image.height / r.height)
            return Color(*image.getpixel((x, y))[:3])


class WindowImageLocator:
    def __init__(self, session, *, locator_factory=PyAutoGuiScreenImageLocator):
        """显式注入窗口 backend，禁止隐式载入桌面截图实现。"""
        self.session = session
        self._locator = locator_factory(backend=session)

    def _local_region(self, region):
        """全局 ROI 仅减一次窗口原点，并拒绝跨窗口区域。"""
        if region is None:
            return None
        r = self.session.window.rect
        local = Rect(
            region.left - r.left, region.top - r.top, region.width, region.height
        )
        if (
            local.left < 0
            or local.top < 0
            or local.left + local.width > r.width
            or local.top + local.height > r.height
        ):
            raise ValueError("图像搜索区域超出固定目标窗口")
        return local

    def _global_rect(self, rect):
        """匹配器返回的局部逻辑矩形仅加一次窗口原点。"""
        if rect is None:
            return None
        r = self.session.window.rect
        return Rect(rect.left + r.left, rect.top + r.top, rect.width, rect.height)

    def _global_match(self, match):
        """保留原始置信度并转换命中矩形。"""
        return (
            None
            if match is None
            else replace(match, rect=self._global_rect(match.rect))
        )

    def locate(self, template, *, region=None, min_confidence=1.0, logger=None):
        """用本会话窗口图查找模板并返回全局逻辑位置。"""
        return self._global_match(
            self._locator.locate(
                template,
                region=self._local_region(region),
                min_confidence=min_confidence,
                logger=logger,
            )
        )

    def locate_requests(
        self,
        requests,
        *,
        logger=None,
        stop_on_first_match=False,
        stop_on_priority_match=False,
    ):
        """一帧完成所有请求，统一转换命中和未命中的最佳矩形。"""
        local = tuple(
            replace(request, region=self._local_region(request.region))
            for request in requests
        )
        results = self._locator.locate_requests(
            local,
            logger=logger,
            stop_on_first_match=stop_on_first_match,
            stop_on_priority_match=stop_on_priority_match,
        )
        return tuple(
            replace(
                result,
                match=self._global_match(result.match),
                best_rect=self._global_rect(result.best_rect),
            )
            for result in results
        )

    def locate_many(
        self,
        templates,
        *,
        region=None,
        min_confidence=1.0,
        logger=None,
        stop_on_first_match=False,
    ):
        """将共享区域查询转换为同帧请求。"""
        return self.locate_requests(
            tuple(
                ImageSearchRequest(template, region, min_confidence)
                for template in templates
            ),
            logger=logger,
            stop_on_first_match=stop_on_first_match,
        )


class WindowStateReader:
    def __init__(self, session):
        """复用既有多点与优先级探测器，只借用统一会话。"""
        self._probe = MacOSWindowStateProbe(
            session.window, session.rules, source=session
        )
        self._backend = session.backend

    def read_current_state(self, *, min_confidence=0.8, logger=None):
        """读取同一源的新画面，保留已配置的逐规则阈值。"""
        result = self._probe.read(default_min_confidence=min_confidence)
        if logger is not None:
            checked = sum(not c.skipped for c in result.candidates)
            logger.log(
                f"screen state backend={self._backend} current_state={result.current_state} elapsed_ms={result.elapsed_ms:.2f} checked={checked} skipped={len(result.candidates) - checked} source_sequence={result.proof.sequence}"
            )
        return result.current_state
