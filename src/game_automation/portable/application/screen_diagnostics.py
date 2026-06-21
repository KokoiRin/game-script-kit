"""编排屏幕诊断类应用用例。

本 module 负责保存截图、诊断状态识别配置、执行一轮状态探测并生成诊断产物；
它不处理 HTTP/CLI/DOM，也不创建真实平台 adapter。调用方通过 factory 注入截图、
屏幕尺寸和图像定位能力，LocalControlApplication 只作为 facade 委托到这里。
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.diagnostic_artifacts import (
    draw_probe_diagnostics,
    draw_region_diagnostics,
    read_image_pixel_size,
    refresh_crop_output_folder,
    save_probe_candidate_crops,
    save_region_crops,
    screen_capture_health_warning,
)
from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    SCREEN_STATE_CONFIG_NAME,
    image_asset_root,
)
from game_automation.portable.application.screen_state_config import (
    load_screen_state_candidates,
    load_screen_state_regions,
)
from game_automation.portable.domain import (
    ImageTemplate,
    Point,
    Rect,
    ScreenStateCandidate,
    ScreenStateProbeResult,
    TargetCatalog,
)
from game_automation.portable.engine.image_query import locate_image
from game_automation.portable.engine.ports import RunLogger, ScreenImageBatchLocator, ScreenImageLocator
from game_automation.portable.engine.screen_state_probe import probe_screen_state

ScreenCapture = Callable[[Path], None]
ScreenCaptureFactory = Callable[[], ScreenCapture]
ScreenSizeFactory = Callable[[], Point]
ScreenImageLocatorFactory = Callable[[], ScreenImageLocator]
ScreenImageBatchLocatorFactory = Callable[[], ScreenImageBatchLocator]

DEBUG_SCREENSHOT_PATH = Path(".star") / "debug" / "screenshots" / "latest-screen.png"
DEBUG_REGION_SCREENSHOT_PATH = Path(".star") / "debug" / "screenshots" / "latest-screen-regions.png"
DEBUG_PROBE_SCREENSHOT_PATH = Path(".star") / "debug" / "screenshots" / "latest-screen-probe.png"
DEBUG_REGION_CROP_FOLDER = Path(".star") / "debug" / "screenshots" / "regions"
DEBUG_PROBE_CROP_FOLDER = Path(".star") / "debug" / "screenshots" / "probe-crops"


@dataclass(frozen=True, slots=True)
class ControlResult:
    """表达本地控制入口可直接展示的退出码、输出和可选截图路径。"""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    screenshot_path: str = ""
    image_size: Point | None = None
    screen_size: Point | None = None


@dataclass(frozen=True, slots=True)
class ImageMatchPreviewResult:
    """表达图片区域预览匹配的结构化结果。"""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    found: bool = False
    confidence: float | None = None
    rect: Rect | None = None
    center: Point | None = None


class _StringLogger:
    def __init__(self) -> None:
        """初始化预览匹配日志缓冲。"""
        self._stream = io.StringIO()

    def log(self, message: str) -> None:
        """把一条诊断日志写入缓冲。"""
        self._stream.write(f"{message}\n")

    def text(self) -> str:
        """返回所有诊断日志文本。"""
        return self._stream.getvalue()


class ScreenDiagnosticsUseCase:
    def __init__(
        self,
        *,
        project_root: Path = PROJECT_ROOT,
        real_image_locator_factory: ScreenImageLocatorFactory | None = None,
        real_image_batch_locator_factory: ScreenImageBatchLocatorFactory | None = None,
        screen_capture_factory: ScreenCaptureFactory | None = None,
        screen_size_factory: ScreenSizeFactory | None = None,
    ) -> None:
        """注入屏幕诊断需要的项目路径和外部能力 factory。"""
        self._project_root = project_root
        self._real_image_locator_factory = real_image_locator_factory
        self._real_image_batch_locator_factory = real_image_batch_locator_factory
        self._screen_capture_factory = screen_capture_factory
        self._screen_size_factory = screen_size_factory

    def capture_screen_screenshot(self) -> ControlResult:
        """保存一张真实屏幕截图，供 UI 诊断截图权限和画面内容。"""
        if self._screen_capture_factory is None:
            return ControlResult(exit_code=1, stderr="screen capture is not configured\n")

        screenshot_path = self.latest_screen_screenshot_path()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._screen_capture_factory()(screenshot_path)
            warning = screen_capture_health_warning(screenshot_path)
            image_size = read_image_pixel_size(screenshot_path)
            screen_size = self._read_screen_size_if_available()
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")
        return ControlResult(
            exit_code=0,
            stdout=f"saved screenshot: {screenshot_path}\n",
            stderr=warning,
            screenshot_path=str(screenshot_path),
            image_size=image_size,
            screen_size=screen_size,
        )

    def preview_image_asset_match(
        self,
        asset_name: str,
        *,
        region: Rect,
        min_confidence: float = 0.8,
    ) -> ImageMatchPreviewResult:
        """在指定区域内只读预览一次图片匹配，不执行点击。"""
        if self._real_image_locator_factory is None:
            return ImageMatchPreviewResult(
                exit_code=1,
                stderr="screen image matching is not configured\n",
            )
        try:
            asset_path = self._resolve_image_asset(asset_name)
            logger = _StringLogger()
            lookup = locate_image(
                ImageTemplate(str(asset_path)),
                image_locator=self._real_image_locator_factory(),
                resources=TargetCatalog(),
                region=region,
                min_confidence=min_confidence,
                logger=logger,
            )
        except ValueError as exc:
            return ImageMatchPreviewResult(exit_code=2, stderr=f"invalid image match preview: {exc}\n")
        except RuntimeError as exc:
            return ImageMatchPreviewResult(exit_code=1, stderr=f"{exc}\n")
        return ImageMatchPreviewResult(
            exit_code=0,
            stdout=logger.text(),
            found=lookup.found,
            confidence=lookup.confidence,
            rect=lookup.rect,
            center=lookup.center,
        )

    def diagnose_screen_setup(self, *, min_confidence: float = 0.8) -> ControlResult:
        """组合截图诊断和单轮状态探测，帮助用户判断屏幕识别环境。"""
        capture_result = self.capture_screen_screenshot()
        if capture_result.exit_code != 0:
            return capture_result

        try:
            probe_result = self.probe_screen_state_once(min_confidence=min_confidence)
        except ValueError as exc:
            return ControlResult(
                exit_code=2,
                stdout=capture_result.stdout,
                stderr=capture_result.stderr + f"screen state probe configuration failed: {exc}\n",
                screenshot_path=capture_result.screenshot_path,
            )
        except RuntimeError as exc:
            return ControlResult(
                exit_code=1,
                stdout=capture_result.stdout,
                stderr=capture_result.stderr + f"screen state probe failed: {exc}\n",
                screenshot_path=capture_result.screenshot_path,
            )

        return ControlResult(
            exit_code=0,
            stdout=capture_result.stdout + screen_diagnosis_probe_stdout(probe_result),
            stderr=capture_result.stderr,
            screenshot_path=capture_result.screenshot_path,
        )

    def capture_screen_region_diagnostics(self) -> ControlResult:
        """保存一张带状态识别区域框的诊断截图。"""
        context = self._screen_region_capture_context()
        if isinstance(context, ControlResult):
            return context
        regions, screen_size = context

        raw_path = self.latest_screen_screenshot_path()
        diagnostic_path = self.latest_screen_region_diagnostics_path()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._screen_capture_factory()(raw_path)
            warning = screen_capture_health_warning(raw_path)
            draw_region_diagnostics(
                screenshot_path=raw_path,
                output_path=diagnostic_path,
                screen_size=screen_size,
                regions=regions,
            )
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")
        return ControlResult(
            exit_code=0,
            stdout=f"saved region diagnostics screenshot: {diagnostic_path}\n",
            stderr=warning,
            screenshot_path=str(diagnostic_path),
        )

    def capture_screen_probe_diagnostics(self, *, min_confidence: float = 0.8) -> ControlResult:
        """保存一张带状态探测候选最佳位置框的诊断截图。"""
        screen_size = self._screen_size_or_error()
        if isinstance(screen_size, ControlResult):
            return screen_size

        raw_path = self.latest_screen_screenshot_path()
        diagnostic_path = self.latest_screen_probe_diagnostics_path()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = self.probe_screen_state_once(min_confidence=min_confidence)
            self._screen_capture_factory()(raw_path)
            warning = screen_capture_health_warning(raw_path)
            draw_probe_diagnostics(
                screenshot_path=raw_path,
                output_path=diagnostic_path,
                screen_size=screen_size,
                regions=self._screen_state_diagnostic_regions(),
                result=result,
            )
        except ValueError as exc:
            return ControlResult(exit_code=2, stderr=f"{exc}\n")
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")
        return ControlResult(
            exit_code=0,
            stdout=(
                f"saved probe diagnostics screenshot: {diagnostic_path}\n"
                f"current_state={result.current_state}\n"
            ),
            stderr=warning,
            screenshot_path=str(diagnostic_path),
        )

    def capture_screen_region_crops(self) -> ControlResult:
        """保存当前屏幕中每个状态识别命名区域的裁剪图。"""
        context = self._screen_region_capture_context()
        if isinstance(context, ControlResult):
            return context
        regions, screen_size = context

        raw_path = self.latest_screen_screenshot_path()
        crop_root = self.latest_screen_region_crop_folder()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        crop_root.mkdir(parents=True, exist_ok=True)
        try:
            self._screen_capture_factory()(raw_path)
            warning = screen_capture_health_warning(raw_path)
            refresh_crop_output_folder(crop_root)
            crop_paths = save_region_crops(
                screenshot_path=raw_path,
                output_folder=crop_root,
                screen_size=screen_size,
                regions=regions,
            )
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")
        return ControlResult(
            exit_code=0,
            stdout="".join(f"saved region crop: {path}\n" for path in crop_paths),
            stderr=warning,
            screenshot_path=str(crop_root),
        )

    def capture_screen_probe_crops(self, *, min_confidence: float = 0.8) -> ControlResult:
        """保存一轮状态探测候选最佳位置裁剪图。"""
        screen_size = self._screen_size_or_error()
        if isinstance(screen_size, ControlResult):
            return screen_size

        raw_path = self.latest_screen_screenshot_path()
        crop_root = self.latest_screen_probe_crop_folder()
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        crop_root.mkdir(parents=True, exist_ok=True)
        try:
            result = self.probe_screen_state_once(min_confidence=min_confidence)
            self._screen_capture_factory()(raw_path)
            warning = screen_capture_health_warning(raw_path)
            refresh_crop_output_folder(crop_root)
            crop_paths = save_probe_candidate_crops(
                screenshot_path=raw_path,
                output_folder=crop_root,
                screen_size=screen_size,
                result=result,
            )
        except ValueError as exc:
            return ControlResult(exit_code=2, stderr=f"{exc}\n")
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")

        stdout = (
            "no probe candidate crops saved\n"
            if not crop_paths
            else "".join(f"saved probe crop: {path}\n" for path in crop_paths)
        )
        return ControlResult(
            exit_code=0,
            stdout=stdout,
            stderr=warning,
            screenshot_path=str(crop_root),
        )

    def probe_screen_state_once(
        self,
        *,
        min_confidence: float = 0.8,
        logger: RunLogger | None = None,
    ) -> ScreenStateProbeResult:
        """使用项目图片资源执行一轮界面状态探测。"""
        return probe_screen_state(
            self._screen_state_candidates(),
            image_locator=self._build_screen_image_locator(),
            batch_image_locator=self._build_screen_image_batch_locator(),
            min_confidence=min_confidence,
            logger=logger,
        )

    def latest_screen_screenshot_path(self) -> Path:
        """返回最近一次截屏诊断保存的项目内文件路径。"""
        return self._project_root / DEBUG_SCREENSHOT_PATH

    def latest_screen_region_diagnostics_path(self) -> Path:
        """返回最近一次区域诊断截图保存的项目内文件路径。"""
        return self._project_root / DEBUG_REGION_SCREENSHOT_PATH

    def latest_screen_probe_diagnostics_path(self) -> Path:
        """返回最近一次探测诊断截图保存的项目内文件路径。"""
        return self._project_root / DEBUG_PROBE_SCREENSHOT_PATH

    def latest_screen_region_crop_folder(self) -> Path:
        """返回最近一次命名区域裁剪图保存的项目内目录。"""
        return self._project_root / DEBUG_REGION_CROP_FOLDER

    def latest_screen_probe_crop_folder(self) -> Path:
        """返回最近一次探测候选裁剪图保存的项目内目录。"""
        return self._project_root / DEBUG_PROBE_CROP_FOLDER

    def _image_asset_root(self) -> Path:
        """返回屏幕诊断读取模板图片和状态配置的目录。"""
        return image_asset_root(self._project_root)

    def _screen_region_capture_context(self):
        """读取状态区域诊断所需的配置、截图能力和屏幕尺寸。"""
        config_path = self._image_asset_root() / SCREEN_STATE_CONFIG_NAME
        if not config_path.exists():
            return ControlResult(
                exit_code=2,
                stderr="screen state config is required for region diagnostics\n",
            )
        try:
            load_screen_state_candidates(
                config_path,
                asset_root=self._image_asset_root(),
                supported_suffixes=IMAGE_ASSET_SUFFIXES,
            )
            regions = load_screen_state_regions(config_path)
        except ValueError as exc:
            return ControlResult(exit_code=2, stderr=f"invalid screen state config: {exc}\n")
        if not regions:
            return ControlResult(exit_code=2, stderr="screen state config has no named regions\n")
        screen_size = self._screen_size_or_error()
        if isinstance(screen_size, ControlResult):
            return screen_size
        return (regions, screen_size)

    def _screen_size_or_error(self) -> Point | ControlResult:
        """读取截图和屏幕尺寸能力，返回用户可见错误或尺寸。"""
        if self._screen_capture_factory is None:
            return ControlResult(exit_code=1, stderr="screen capture is not configured\n")
        if self._screen_size_factory is None:
            return ControlResult(exit_code=1, stderr="screen size is not configured\n")
        try:
            return self._screen_size_factory()
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")

    def _read_screen_size_if_available(self) -> Point | None:
        """尽力读取屏幕坐标尺寸，失败时不影响普通截图展示。"""
        if self._screen_size_factory is None:
            return None
        try:
            return self._screen_size_factory()
        except Exception:
            return None

    def _screen_state_diagnostic_regions(self):
        """读取探测诊断可选绘制的命名区域。"""
        config_path = self._image_asset_root() / SCREEN_STATE_CONFIG_NAME
        if not config_path.exists():
            return ()
        return load_screen_state_regions(config_path)

    def _screen_state_candidates(self) -> tuple[ScreenStateCandidate, ...]:
        """优先从状态配置读取候选，没有配置时扫描 assets 图片。"""
        configured_candidates = load_screen_state_candidates(
            self._image_asset_root() / SCREEN_STATE_CONFIG_NAME,
            asset_root=self._image_asset_root(),
            supported_suffixes=IMAGE_ASSET_SUFFIXES,
        )
        if configured_candidates is not None:
            return configured_candidates
        return tuple(
            ScreenStateCandidate(
                name=Path(asset_name).stem,
                search=ImageTemplate(str(self._resolve_image_asset(asset_name))),
            )
            for asset_name in self._list_image_assets()
        )

    def _list_image_assets(self) -> tuple[str, ...]:
        """列出诊断可用的图片资源文件名。"""
        asset_root = self._image_asset_root()
        if not asset_root.is_dir():
            return ()
        return tuple(
            sorted(
                path.name
                for path in asset_root.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_ASSET_SUFFIXES
            )
        )

    def _resolve_image_asset(self, asset_name: str) -> Path:
        """解析并校验图片资源必须位于项目 assets 目录内。"""
        candidate = (self._image_asset_root() / asset_name).resolve()
        asset_root = self._image_asset_root().resolve()
        try:
            candidate.relative_to(asset_root)
        except ValueError as exc:
            raise ValueError("image asset must stay inside assets folder") from exc
        if not candidate.is_file() or candidate.suffix.lower() not in IMAGE_ASSET_SUFFIXES:
            raise ValueError("image asset does not exist or has unsupported suffix")
        return candidate

    def _build_screen_image_locator(self) -> ScreenImageLocator | None:
        """创建真实图像定位 adapter，未装配时返回 None。"""
        return None if self._real_image_locator_factory is None else self._real_image_locator_factory()

    def _build_screen_image_batch_locator(self) -> ScreenImageBatchLocator | None:
        """创建真实批量图像定位 adapter，未装配时返回 None。"""
        if self._real_image_batch_locator_factory is None:
            return None
        return self._real_image_batch_locator_factory()


def screen_diagnosis_probe_stdout(result: ScreenStateProbeResult) -> str:
    """把单轮状态探测结果格式化为屏幕诊断摘要。"""
    lines = [
        f"current_state={result.current_state}",
        f"elapsed_ms={result.elapsed_ms:.2f}",
    ]
    lines.extend(_screen_diagnosis_candidate_line(candidate) for candidate in result.candidates)
    lines.extend(f"hint={hint}" for hint in result.hints)
    return "".join(f"{line}\n" for line in lines)


def _screen_diagnosis_candidate_line(candidate) -> str:
    """把单个状态候选格式化为屏幕诊断摘要行。"""
    name = candidate.candidate.name
    if candidate.candidate.search_name:
        name = f"{name}/{candidate.candidate.search_name}"
    return (
        f"candidate={name} "
        f"status={_screen_diagnosis_candidate_status(candidate)} "
        f"elapsed_ms={candidate.elapsed_ms:.2f} "
        f"confidence={_screen_diagnosis_optional_confidence(candidate.confidence)} "
        f"best_confidence={_screen_diagnosis_optional_confidence(candidate.best_confidence)} "
        f"best_rect={_screen_diagnosis_optional_rect(candidate.best_rect)}"
    )


def _screen_diagnosis_candidate_status(candidate) -> str:
    """返回屏幕诊断摘要使用的候选状态枚举。"""
    if candidate.skipped:
        return "skipped"
    if candidate.found:
        return "matched"
    return "missed"


def _screen_diagnosis_optional_confidence(confidence: float | None) -> str:
    """把可空置信度格式化为屏幕诊断摘要文本。"""
    return "None" if confidence is None else f"{confidence:.3f}"


def _screen_diagnosis_optional_rect(rect) -> str:
    """把可空矩形格式化为屏幕诊断摘要文本。"""
    if rect is None:
        return "None"
    return f"x={rect.left},y={rect.top},w={rect.width},h={rect.height}"
