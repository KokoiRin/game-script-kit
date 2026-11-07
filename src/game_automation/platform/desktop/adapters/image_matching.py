"""实现 engine.ports.ScreenImageLocator，通过 pyautogui 截图和 OpenCV 定位模板图像。

本 module 只封装桌面截图、模板读取、OpenCV 匹配和后端错误转换；它不定义
脚本条件语义，也不决定图像匹配能力何时被装配到 runner。
"""

from __future__ import annotations

from game_automation.portable.application.capture_errors import WindowCaptureError

import threading
from dataclasses import dataclass, replace
from pathlib import Path
from time import perf_counter
from types import ModuleType

from PIL import Image

from game_automation.platform.desktop.adapters.screen_capture import (
    CapturedScreen,
    capture_screen as _capture_screen,
    crop_captured_screen as _crop_captured_screen,
)
from game_automation.portable.domain import ImageBatchMatchResult, ImageMatch, ImageSearchRequest, ImageTemplate, Rect
from game_automation.portable.engine.ports import RunLogger, ScreenImageLocator


class PyAutoGuiScreenImageLocator(ScreenImageLocator):
    def __init__(self, backend: object | None = None) -> None:
        """初始化屏幕图像定位 adapter，可注入 backend 便于测试。"""
        self._backend = backend if backend is not None else self._load_backend()

    def locate(
        self,
        template: ImageTemplate,
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger: RunLogger | None = None,
    ) -> ImageMatch | None:
        """在当前屏幕或指定区域内查找模板图片。"""
        _validate_min_confidence(min_confidence)
        try:
            total_started_at = perf_counter()
            cv_started_at = perf_counter()
            cv2, numpy = _load_cv_modules()
            cv_load_ms = _elapsed_ms(cv_started_at)
            screenshot_started_at = perf_counter()
            screenshot = _capture_screen(self._backend, region=region)
            screenshot_ms = _elapsed_ms(screenshot_started_at)
            template_started_at = perf_counter()
            template_image = self._load_template_image(template, numpy)
            template_load_ms = _elapsed_ms(template_started_at)
            match_started_at = perf_counter()
            located = _locate_template(
                cv2=cv2,
                numpy=numpy,
                screenshot=screenshot,
                template=template_image,
                min_confidence=min_confidence,
            )
            match = located.match
            match_ms = _elapsed_ms(match_started_at)
            _log_match_stages(
                logger,
                template=template,
                region=region,
                screenshot=screenshot,
                template_image=template_image.image,
                cv_load_ms=cv_load_ms,
                screenshot_ms=screenshot_ms,
                template_load_ms=template_load_ms,
                match_ms=match_ms,
                total_ms=_elapsed_ms(total_started_at),
                match=match,
            )
            return match
        except Exception as exc:
            if isinstance(exc, WindowCaptureError) or _is_setup_error(exc):
                raise exc
            raise RuntimeError(
                "failed to perform screen image matching. Check template path, "
                "screenshot permissions, and image matching dependencies."
            ) from exc

    def locate_many(
        self,
        templates: tuple[ImageTemplate, ...],
        *,
        region: Rect | None = None,
        min_confidence: float = 1.0,
        logger: RunLogger | None = None,
        stop_on_first_match: bool = False,
    ) -> tuple[ImageBatchMatchResult, ...]:
        """在一次截图中查找多张模板图片。"""
        _validate_min_confidence(min_confidence)
        return self.locate_requests(
            tuple(
                ImageSearchRequest(
                    template=template,
                    region=region,
                    min_confidence=min_confidence,
                )
                for template in templates
            ),
            logger=logger,
            stop_on_first_match=stop_on_first_match,
        )

    def locate_requests(
        self,
        requests: tuple[ImageSearchRequest, ...],
        *,
        logger: RunLogger | None = None,
        stop_on_first_match: bool = False,
        stop_on_priority_match: bool = False,
    ) -> tuple[ImageBatchMatchResult, ...]:
        """在一次截图中查找多条图片搜索请求。"""
        if stop_on_first_match and stop_on_priority_match:
            raise ValueError('first-match and priority-match modes are mutually exclusive')
        try:
            total_started_at = perf_counter()
            cv_started_at = perf_counter()
            cv2 = numpy = None
            cv_load_ms = 0.0
            screenshot_started_at = perf_counter()
            screenshot = _capture_screen(self._backend, region=None)
            screenshot_ms = _elapsed_ms(screenshot_started_at)
            results = [replace(ImageBatchMatchResult.skipped_result(r.template), point_count=None if r.pattern is None else len(r.pattern.points)) for r in requests]
            order = sorted(range(len(requests)), key=lambda i: -requests[i].priority) if stop_on_priority_match else range(len(requests))
            matched_priority = None
            template_load_ms = 0.0
            match_ms = 0.0
            screenshot_array = None
            for index in order:
                request = requests[index]
                if stop_on_priority_match and matched_priority is not None and request.priority < matched_priority:
                    break
                if request.pattern is not None:
                    from game_automation.platform.desktop.adapters.color_matching import locate_color_pattern
                    point_started = perf_counter()
                    located = locate_color_pattern(screenshot, request.template, request.pattern)
                    one_match_ms = _elapsed_ms(point_started)
                    results[index] = replace(located, elapsed_ms=one_match_ms)
                    match_ms += one_match_ms
                    if located.match is not None:
                        if stop_on_priority_match:
                            matched_priority = request.priority
                        if stop_on_first_match:
                            break
                    continue
                if numpy is None:
                    cv_started_at = perf_counter()
                    cv2, numpy = _load_cv_modules()
                    cv_load_ms += _elapsed_ms(cv_started_at)
                    array_started = perf_counter()
                    screenshot_array = numpy.array(screenshot.image)
                    match_ms += _elapsed_ms(array_started)
                template_started_at = perf_counter()
                template = request.template
                template_image = self._load_template_image(template, numpy)
                template_load_ms += _elapsed_ms(template_started_at)
                search_screen = (
                    screenshot
                    if request.region is None
                    else _crop_captured_screen(screenshot, region=request.region)
                )
                search_array = screenshot_array if request.region is None else numpy.array(search_screen.image)
                match_started_at = perf_counter()
                located = _locate_template(
                    cv2=cv2,
                    numpy=numpy,
                    screenshot=search_screen,
                    screenshot_array=search_array,
                    template=template_image,
                    min_confidence=request.min_confidence,
                )
                match = located.match
                one_match_ms = _elapsed_ms(match_started_at)
                match_ms += one_match_ms
                results[index] = ImageBatchMatchResult(
                        template=template,
                        match=match,
                        elapsed_ms=one_match_ms,
                        best_confidence=located.best_confidence,
                        best_rect=located.best_rect,
                    )
                if stop_on_priority_match and match is not None:
                    matched_priority = request.priority
                if stop_on_first_match and match is not None:
                    break
            batch_results = tuple(results)
            _log_batch_match_stages(
                logger,
                requests=requests,
                screenshot=screenshot,
                cv_load_ms=cv_load_ms,
                screenshot_ms=screenshot_ms,
                template_load_ms=template_load_ms,
                match_ms=match_ms,
                total_ms=_elapsed_ms(total_started_at),
                results=batch_results,
            )
            return batch_results
        except Exception as exc:
            if isinstance(exc, WindowCaptureError) or _is_setup_error(exc):
                raise exc
            raise RuntimeError(
                "failed to perform screen image matching. Check template path, "
                "screenshot permissions, and image matching dependencies."
            ) from exc

    def _load_backend(self) -> object:
        """延迟加载 pyautogui，避免导入工具模块时触发平台依赖。"""
        try:
            import pyautogui
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "pyautogui is required for screen image matching. "
                "Install dependencies with: pip install -e \".[dev]\""
            ) from exc
        return pyautogui

    def _load_template_image(self, template: ImageTemplate, numpy: ModuleType) -> LoadedTemplateImage:
        """读取并缓存模板图片和 OpenCV 数组。"""
        template_path = Path(template.path)
        with _TEMPLATE_CACHE_LOCK:
            stat = template_path.stat()
            cached = _TEMPLATE_CACHE.get(template_path)
            if (
                cached is not None
                and cached.mtime_ns == stat.st_mtime_ns
                and cached.size_bytes == stat.st_size
            ):
                return cached.image
            image = _load_template_image(template, numpy)
            _TEMPLATE_CACHE[template_path] = TemplateCacheEntry(
                mtime_ns=stat.st_mtime_ns,
                size_bytes=stat.st_size,
                image=image,
            )
            return image


@dataclass(frozen=True, slots=True)
class LoadedTemplateImage:
    image: Image.Image
    array: object


@dataclass(frozen=True, slots=True)
class LocatedTemplate:
    match: ImageMatch | None
    best_confidence: float | None
    best_rect: Rect | None


@dataclass(frozen=True, slots=True)
class TemplateCacheEntry:
    mtime_ns: int
    size_bytes: int
    image: LoadedTemplateImage


_TEMPLATE_CACHE: dict[Path, TemplateCacheEntry] = {}
_TEMPLATE_CACHE_LOCK = threading.Lock()


def _elapsed_ms(started_at: float) -> float:
    """把 perf_counter 起点转换成毫秒耗时。"""
    return (perf_counter() - started_at) * 1000


def _load_cv_modules() -> tuple[ModuleType, ModuleType]:
    """延迟加载 OpenCV 和 numpy，避免普通导入触发图像匹配依赖。"""
    try:
        import cv2
        import numpy
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "OpenCV-backed screen image matching requires opencv-python-headless "
            "and numpy. Install dependencies with: pip install -e ."
        ) from exc
    return cv2, numpy


def _load_template_image(template: ImageTemplate, numpy: ModuleType) -> LoadedTemplateImage:
    """读取模板图片并转换为 OpenCV 可匹配的 RGB 图。"""
    with Image.open(Path(template.path)) as image:
        template_image = image.convert("RGB")
    return LoadedTemplateImage(image=template_image, array=numpy.array(template_image))


def _locate_template(
    *,
    cv2: ModuleType,
    numpy: ModuleType,
    screenshot: CapturedScreen,
    template: LoadedTemplateImage,
    min_confidence: float,
    screenshot_array: object | None = None,
) -> LocatedTemplate:
    """用 OpenCV 模板匹配返回满足阈值的最佳匹配。"""
    if template.image.width > screenshot.image.width or template.image.height > screenshot.image.height:
        return LocatedTemplate(match=None, best_confidence=None, best_rect=None)

    if screenshot_array is None:
        screenshot_array = numpy.array(screenshot.image)
    result = cv2.matchTemplate(screenshot_array, template.array, cv2.TM_CCOEFF_NORMED)
    _, max_score, _, max_location = cv2.minMaxLoc(result)
    confidence = _clamp_opencv_confidence(float(max_score))
    left_pixels = int(max_location[0]) + screenshot.origin_left_pixels
    top_pixels = int(max_location[1]) + screenshot.origin_top_pixels
    best_rect = Rect(
        left=round(left_pixels / screenshot.pixels_per_point_x),
        top=round(top_pixels / screenshot.pixels_per_point_y),
        width=round(template.image.width / screenshot.pixels_per_point_x),
        height=round(template.image.height / screenshot.pixels_per_point_y),
    )
    if confidence < min_confidence:
        return LocatedTemplate(match=None, best_confidence=confidence, best_rect=best_rect)

    match = ImageMatch(
        rect=best_rect,
        confidence=confidence,
    )
    return LocatedTemplate(match=match, best_confidence=confidence, best_rect=best_rect)


def _log_match_stages(
    logger: RunLogger | None,
    *,
    template: ImageTemplate,
    region: Rect | None,
    screenshot: CapturedScreen,
    template_image: Image.Image,
    cv_load_ms: float,
    screenshot_ms: float,
    template_load_ms: float,
    match_ms: float,
    total_ms: float,
    match: ImageMatch | None,
) -> None:
    """记录桌面图像匹配各阶段耗时，帮助定位性能瓶颈。"""
    if logger is None:
        return
    logger.log(
        "image match stages "
        f"template={template.path} "
        f"region={region} "
        f"screenshot_size={screenshot.image.width}x{screenshot.image.height} "
        f"template_size={template_image.width}x{template_image.height} "
        f"cv_load_ms={cv_load_ms:.2f} "
        f"screenshot_ms={screenshot_ms:.2f} "
        f"template_load_ms={template_load_ms:.2f} "
        f"match_ms={match_ms:.2f} "
        f"total_ms={total_ms:.2f} "
        f"found={match is not None} "
        f"confidence={None if match is None else match.confidence}"
    )


def _clamp_opencv_confidence(score: float) -> float:
    """把 OpenCV 归一化匹配分数限制在领域允许的置信度范围内。"""
    # OpenCV 的归一化匹配在极高相似度时可能因浮点误差略微超过 1。
    return max(0.0, min(1.0, score))


def _log_batch_match_stages(
    logger: RunLogger | None,
    *,
    requests: tuple[ImageSearchRequest, ...],
    screenshot: CapturedScreen,
    cv_load_ms: float,
    screenshot_ms: float,
    template_load_ms: float,
    match_ms: float,
    total_ms: float,
    results: tuple[ImageBatchMatchResult, ...],
) -> None:
    """记录桌面批量图像匹配各阶段耗时，帮助定位性能瓶颈。"""
    if logger is None:
        return
    logger.log(
        "image batch match stages "
        f"template_count={len(requests)} "
        f"region_count={sum(1 for request in requests if request.region is not None)} "
        f"screenshot_size={screenshot.image.width}x{screenshot.image.height} "
        f"cv_load_ms={cv_load_ms:.2f} "
        f"screenshot_ms={screenshot_ms:.2f} "
        f"template_load_ms={template_load_ms:.2f} "
        f"match_ms={match_ms:.2f} "
        f"total_ms={total_ms:.2f} "
        f"checked_count={sum(1 for result in results if result.found or not result.skipped)} "
        f"skipped_count={sum(1 for result in results if result.skipped)} "
        f"found_count={sum(1 for result in results if result.found)}"
    )


def _is_setup_error(exc: Exception) -> bool:
    """判断异常是否已经是本 adapter 生成的清晰 setup 错误。"""
    return isinstance(exc, RuntimeError) and (
        "OpenCV-backed screen image matching" in str(exc)
        or "screen pointer size" in str(exc)
    )


def _validate_min_confidence(min_confidence: float) -> None:
    """校验最低匹配置信度必须大于 0 且不超过 1。"""
    if not 0 < min_confidence <= 1:
        raise ValueError("minimum image match confidence must be greater than 0 and at most 1")
