"""为本地控制 UI 提供应用层用例。

本 module 收敛 UI 需要的脚本列表、命名脚本运行和固定测试任务能力；它不渲染
HTML、不解析 HTTP，也不直接解释脚本步骤或创建平台自动化 adapter。
"""

from __future__ import annotations

import io
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from game_automation.portable.application.script_run import (
    InputDeviceFactory,
    PixelColorReaderFactory,
    ScreenImageLocatorFactory,
    run_script,
)
from game_automation.portable.domain import Click, ImageTarget, ImageTemplate, ScreenWindow, Script
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptCatalog, ScriptNotFoundError

CommandRunner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]
ScreenCapture = Callable[[Path], None]
ScreenCaptureFactory = Callable[[], ScreenCapture]

PROJECT_ROOT = Path(__file__).resolve().parents[4]
IMAGE_ASSET_FOLDER = "assets"
IMAGE_ASSET_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
DEBUG_SCREENSHOT_PATH = Path(".star") / "debug" / "screenshots" / "latest-screen.png"


@dataclass(frozen=True, slots=True)
class ControlResult:
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    screenshot_path: str = ""


class LocalControlApplication:
    def __init__(
        self,
        catalog: ScriptCatalog = DEFAULT_SCRIPT_CATALOG,
        *,
        command_runner: CommandRunner | None = None,
        project_root: Path = PROJECT_ROOT,
        real_device_factory: InputDeviceFactory | None = None,
        real_color_reader_factory: PixelColorReaderFactory | None = None,
        real_image_locator_factory: ScreenImageLocatorFactory | None = None,
        screen_capture_factory: ScreenCaptureFactory | None = None,
    ) -> None:
        """注入 UI 用例需要的脚本 catalog、项目路径和外部能力工厂。"""
        self._catalog = catalog
        self._command_runner = command_runner if command_runner is not None else _run_command
        self._project_root = project_root
        self._real_device_factory = real_device_factory
        self._real_color_reader_factory = real_color_reader_factory
        self._real_image_locator_factory = real_image_locator_factory
        self._screen_capture_factory = screen_capture_factory
        self._test_tasks: dict[str, tuple[str, ...]] = {
            "all": (sys.executable, "-m", "pytest"),
        }

    def list_scripts(self) -> tuple[str, ...]:
        """返回 UI 可展示的脚本名称列表。"""
        return self._catalog.list_names()

    def image_asset_folder_label(self) -> str:
        """返回用户应放置模板图片的项目内目录名。"""
        return IMAGE_ASSET_FOLDER

    def list_image_assets(self) -> tuple[str, ...]:
        """列出项目图片资源目录中的可用模板图片。"""
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

    def run_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str = "#000000",
    ) -> ControlResult:
        """按名称运行脚本，并捕获入口层可展示的输出。"""
        try:
            script = self._catalog.get(name)
        except ScriptNotFoundError as exc:
            return ControlResult(exit_code=1, stderr=str(exc))

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_color=dry_run_color,
                real_device_factory=self._real_device_factory,
                real_color_reader_factory=self._real_color_reader_factory,
                real_image_locator_factory=self._real_image_locator_factory,
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def click_image_asset(self, asset_name: str, *, dry_run: bool) -> ControlResult:
        """把项目图片资源作为模板目标，运行一次查找并点击脚本。"""
        try:
            asset_path = self._resolve_image_asset(asset_name)
        except ValueError:
            return ControlResult(exit_code=2, stderr=f"invalid image asset: {asset_name}\n")

        script = Script(
            name="click-image-asset",
            window=ScreenWindow(),
            steps=(Click(ImageTarget(ImageTemplate(str(asset_path)))),),
        )

        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = run_script(
                script,
                dry_run=dry_run,
                dry_run_images=(str(asset_path),) if dry_run else (),
                real_device_factory=self._real_device_factory,
                real_image_locator_factory=self._real_image_locator_factory,
            )

        if result.error_message is not None:
            stderr.write(result.error_message)
            stderr.write("\n")
        return ControlResult(
            exit_code=result.exit_code,
            stdout=stdout.getvalue(),
            stderr=stderr.getvalue(),
        )

    def capture_screen_screenshot(self) -> ControlResult:
        """保存一张真实屏幕截图，供 UI 诊断截图权限和画面内容。"""
        if self._screen_capture_factory is None:
            return ControlResult(exit_code=1, stderr="screen capture is not configured\n")

        screenshot_path = self.latest_screen_screenshot_path()
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._screen_capture_factory()(screenshot_path)
        except Exception as exc:
            return ControlResult(exit_code=1, stderr=f"{exc}\n")
        return ControlResult(
            exit_code=0,
            stdout=f"saved screenshot: {screenshot_path}\n",
            screenshot_path=str(screenshot_path),
        )

    def latest_screen_screenshot_path(self) -> Path:
        """返回最近一次截屏诊断保存的项目内文件路径。"""
        return self._project_root / DEBUG_SCREENSHOT_PATH

    def run_tests(self, task_name: str = "all") -> ControlResult:
        """运行白名单测试任务，并返回 UI 可展示的执行结果。"""
        command = self._test_tasks.get(task_name)
        if command is None:
            return ControlResult(
                exit_code=2,
                stderr=f"unknown test task: {task_name}\n",
            )

        completed = self._command_runner(command, self._project_root)
        return ControlResult(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def _image_asset_root(self) -> Path:
        """返回本地 UI 允许读取模板图片的项目内目录。"""
        return self._project_root / IMAGE_ASSET_FOLDER

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


def _run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """执行 application 层白名单命令，不经过 shell。"""
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
