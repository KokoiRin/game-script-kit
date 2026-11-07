"""为实时观察捕获指定 macOS 窗口并批量匹配状态素材。

本 module 默认从目标窗口流读取独立画面，不激活窗口或发送输入；
复用现有 OpenCV 匹配器，返回窗口相对的识别证据而不解释任务动作。
"""

from pathlib import Path
import subprocess
import tempfile
from time import perf_counter

from PIL import Image

from game_automation.portable.domain.screen_state import ProbeTiming
from game_automation.platform.macos.adapters.window_identity import BoundWindow

from game_automation.portable.application.capture_errors import WindowCaptureError
from game_automation.platform.desktop.adapters.image_matching import PyAutoGuiScreenImageLocator
from game_automation.portable.domain import ImageSearchRequest, ScreenStateCandidateResult, ScreenStateProbeResult


class WindowFrameSource:
    def __init__(self, window, *, quartz=None, command_runner=None) -> None:
        """绑定已选择窗口和可注入系统边界，创建有界临时目录。"""
        self.window = window
        self._quartz = quartz
        self._command = subprocess.run if command_runner is None else command_runner
        self._cache = tempfile.TemporaryDirectory(prefix='star-observer-')
        self._size = (window.rect.width, window.rect.height)
        try:
            self._binding = BoundWindow(window, quartz=quartz)
            self._quartz = self._binding.quartz
        except BaseException:
            self._cache.cleanup()
            raise

    def _selected_window(self):
        """复用请求式和持续采集共用的身份校验。"""
        return self._binding.check()

    def screenshot(self):
        """重新核对已绑定窗口后采集，失败不返回上一帧。"""
        item = self._selected_window()
        q = self._quartz
        path = Path(self._cache.name) / 'current.png'
        path.unlink(missing_ok=True)
        try:
            self._command(['/usr/sbin/screencapture', '-x', '-o', '-l', str(item[q.kCGWindowNumber]), str(path)],
                          capture_output=True, check=True, timeout=2)
            with Image.open(path) as image:
                return image.convert('RGB')
        except (OSError, subprocess.SubprocessError) as exc:
            raise WindowCaptureError('窗口截图失败，请检查屏幕截图权限和目标窗口是否可用') from exc

    def size(self):
        """返回本轮窗口的逻辑尺寸，供 Retina 坐标换算。"""
        return self._size

    def close(self) -> None:
        """释放本窗口探测器拥有的临时截图。"""
        self._cache.cleanup()


class MacOSWindowStateProbe:
    def __init__(self, window, rules, *, source=None, hz=2) -> None:
        """验证模板采集尺寸并装配只读的一帧批量定位。"""
        if (window.rect.width, window.rect.height) != (rules.width, rules.height):
            raise ValueError('窗口尺寸与状态素材不同，请恢复采集时的窗口尺寸')
        self._pixel_size = (rules.pixel_width, rules.pixel_height)
        if None in self._pixel_size:
            if source is not None:
                source.close()
            raise ValueError('状态素材缺少截图像素尺寸，请重新采集素材')
        if source is None:
            from game_automation.platform.macos.adapters.window_stream import WindowStreamSource
            source = WindowStreamSource(window, self._pixel_size, hz=hz)
        self._source = source
        self._proof = None
        self._locator = PyAutoGuiScreenImageLocator(backend=self)
        self._candidates = rules.candidates
        self._priorities = rules.priorities
        self._patterns = rules.patterns
        self._screenshot_ms = 0.0

    def screenshot(self):
        """验证完整截图像素尺寸，禁止隐式跨缩放匹配。"""
        started = perf_counter()
        image = self._source.screenshot()
        if image.size != self._pixel_size:
            image.close()
            raise WindowCaptureError('窗口截图像素尺寸已变化，请恢复显示缩放或重新采集素材')
        self._proof = getattr(self._source, 'proof', None)
        self._screenshot_ms += (perf_counter() - started) * 1000
        return image

    def size(self):
        """把原始窗口逻辑尺寸交给既有匹配器。"""
        return self._source.size()

    @property
    def candidate_count(self) -> int:
        """返回本探测器配置的搜索素材数量。"""
        return len(self._candidates)

    def read(self) -> ScreenStateProbeResult:
        """在同一张窗口截图中按优先级核对，命中后跳过低层素材。"""
        started = perf_counter()
        self._screenshot_ms = 0.0
        self._proof = None
        requests = tuple(ImageSearchRequest(c.template, c.search.region, c.search.min_confidence or 0.9, priority, pattern)
                         for c, priority, pattern in zip(self._candidates, self._priorities, self._patterns, strict=True))
        results = self._locator.locate_requests(requests, stop_on_priority_match=True)
        candidates = tuple(ScreenStateCandidateResult(c, r.match, r.elapsed_ms,
            skipped=r.skipped, best_confidence=r.best_confidence, best_rect=r.best_rect, priority=priority, matched_points=r.matched_points, point_count=r.point_count)
            for c, r, priority in zip(self._candidates, results, self._priorities, strict=True))
        elapsed = (perf_counter() - started) * 1000
        return ScreenStateProbeResult(candidates, elapsed,
            ProbeTiming(self._screenshot_ms, max(0.0, elapsed - self._screenshot_ms),
                        getattr(self._source, 'capture_mode', 'snapshot')), self._proof)

    def close(self) -> None:
        """关闭本次观察的截图资源。"""
        self._source.close()
