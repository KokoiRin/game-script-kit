"""按脚本需要读取当前界面状态。

本 module 从项目状态配置组装一次识图请求，通过注入的定位端口返回状态名称；
它不创建平台 adapter、不保存截图，也不启动探测线程或复用旧的状态结果。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    image_asset_root,
    screen_state_config_path,
)
from game_automation.portable.application.screen_state_config import (
    load_screen_state_candidates,
)
from game_automation.portable.domain import ImageTemplate, ScreenStateCandidate
from game_automation.portable.engine.ports import (
    RunLogger,
    ScreenImageBatchLocator,
    ScreenImageLocator,
    ScreenStateReader,
)
from game_automation.portable.engine.screen_state_probe import probe_screen_state

ScreenImageLocatorFactory = Callable[[], ScreenImageLocator]
ScreenImageBatchLocatorFactory = Callable[[], ScreenImageBatchLocator]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectScreenStateReader(ScreenStateReader):
    """把项目配置与外部定位能力收敛成脚本运行时的状态端口。"""

    project_root: Path = PROJECT_ROOT
    real_image_locator_factory: ScreenImageLocatorFactory | None = None
    real_image_batch_locator_factory: ScreenImageBatchLocatorFactory | None = None

    def read_current_state(
        self,
        *,
        min_confidence: float = 0.8,
        logger: RunLogger | None = None,
    ) -> str:
        """每次重新读取配置和当前画面，返回这一轮匹配到的状态。"""
        try:
            candidates = self._load_candidates()
        except (LookupError, OSError, ValueError) as exc:
            # 运行期间配置也可能被修改；转成 runner 已约定的运行失败结果。
            raise RuntimeError(f"screen state configuration failed: {exc}") from exc
        batch_locator = (
            None
            if self.real_image_batch_locator_factory is None
            else self.real_image_batch_locator_factory()
        )
        image_locator = (
            None
            if batch_locator is not None or self.real_image_locator_factory is None
            else self.real_image_locator_factory()
        )
        result = probe_screen_state(
            candidates,
            image_locator=image_locator,
            batch_image_locator=batch_locator,
            min_confidence=min_confidence,
            logger=logger,
        )
        if logger is not None:
            logger.log(
                "screen state probe round "
                f"current_state={result.current_state} elapsed_ms={result.elapsed_ms:.2f}"
            )
        return result.current_state

    def _load_candidates(self) -> tuple[ScreenStateCandidate, ...]:
        """优先使用显式状态配置，缺少配置时保留按模板文件名识别的行为。"""
        asset_root = image_asset_root(self.project_root)
        configured = load_screen_state_candidates(
            screen_state_config_path(self.project_root),
            asset_root=asset_root,
            supported_suffixes=IMAGE_ASSET_SUFFIXES,
        )
        if configured is not None:
            return configured
        if not asset_root.is_dir():
            return ()
        return tuple(
            ScreenStateCandidate(path.stem, ImageTemplate(str(path.resolve())))
            for path in sorted(asset_root.iterdir())
            if path.is_file() and path.suffix.lower() in IMAGE_ASSET_SUFFIXES
        )
