"""star 命令行入口。

本 module 负责解析命令行参数、查找内置脚本并打印用户可见结果；脚本运行和
本地 UI 委托应用/入口编排层，recorder 子命令保留终端工具组装但不解释脚本步骤。
"""

from __future__ import annotations

import argparse
import sys

from game_automation.platform.local_desktop.composition import run_script_on_local_desktop
from game_automation.portable.application.project_assets import (
    IMAGE_ASSET_SUFFIXES,
    PROJECT_ROOT,
    SCREEN_STATE_CONFIG_NAME,
    image_asset_root,
)
from game_automation.portable.application.screen_state_config import load_screen_state_names
from game_automation.portable.application.script_details import ScriptDetailsResult, describe_script_details
from game_automation.portable.application.script_resources import (
    load_shared_script_resources,
    script_with_shared_resources,
)
from game_automation.portable.scripts_manager import DEFAULT_SCRIPT_CATALOG
from game_automation.portable.scripts_manager.catalog import ScriptNotFoundError


def _run_list() -> int:
    """列出所有可用脚本。"""
    for name in DEFAULT_SCRIPT_CATALOG.list_names():
        print(name)
    return 0


def _run_script(args: argparse.Namespace) -> int:
    """按名称运行脚本。"""
    if args.dry_run_script_images and not args.dry_run:
        print("--dry-run-script-images requires --dry-run", file=sys.stderr)
        return 2
    try:
        script = DEFAULT_SCRIPT_CATALOG.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    try:
        script = script_with_shared_resources(script, load_shared_script_resources(PROJECT_ROOT))
    except (LookupError, ValueError) as exc:
        print(f"script resource configuration failed: {exc}", file=sys.stderr)
        return 2

    dry_run_images = tuple(args.dry_run_image)
    if args.dry_run_script_images:
        try:
            dry_run_images = _merge_dry_run_images(
                dry_run_images,
                _describe_script(script).image_dependencies,
            )
        except (LookupError, ValueError) as exc:
            print(f"script details configuration failed: {exc}", file=sys.stderr)
            return 2

    result = run_script_on_local_desktop(
        script,
        dry_run=args.dry_run,
        dry_run_color=args.dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=args.dry_run_screen_state,
    )
    if result.error_message is not None:
        print(result.error_message, file=sys.stderr)
    return result.exit_code


def _run_details(args: argparse.Namespace) -> int:
    """按名称展示脚本详情。"""
    try:
        script = DEFAULT_SCRIPT_CATALOG.get(args.name)
    except ScriptNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1
    try:
        script = script_with_shared_resources(script, load_shared_script_resources(PROJECT_ROOT))
        details = _describe_script(script)
    except (LookupError, ValueError) as exc:
        print(f"script details configuration failed: {exc}", file=sys.stderr)
        return 2
    _print_script_details(details)
    return details.exit_code


def _describe_script(script) -> ScriptDetailsResult:
    """生成 CLI 复用的脚本详情。"""
    return describe_script_details(
        script,
        asset_root=image_asset_root(PROJECT_ROOT),
        supported_image_suffixes=IMAGE_ASSET_SUFFIXES,
        state_names=_configured_screen_state_names(),
    )


def _merge_dry_run_images(
    explicit_images: tuple[str, ...],
    script_images: tuple[str, ...],
) -> tuple[str, ...]:
    """合并用户显式 dry-run 图片和脚本解析出的图片依赖。"""
    return tuple(dict.fromkeys((*explicit_images, *script_images)))


def _configured_screen_state_names() -> tuple[str, ...] | None:
    """读取状态配置中的状态名，配置不可用时返回 None。"""
    try:
        return load_screen_state_names(image_asset_root(PROJECT_ROOT) / SCREEN_STATE_CONFIG_NAME)
    except ValueError:
        return None


def _print_script_details(details: ScriptDetailsResult) -> None:
    """把脚本详情结果打印成稳定的 CLI 文本。"""
    if details.exit_code != 0:
        print(details.stderr, file=sys.stderr, end="")
        return
    print(f"脚本：{details.name}")
    _print_section("步骤", details.steps)
    _print_section("依赖", details.dependencies)
    _print_section("图片依赖", details.image_dependencies)
    _print_section(
        "依赖检查",
        tuple(
            f"{_readiness_status_label(status)} {label}：{message}"
            for label, status, message in details.readiness
        ),
    )


def _print_section(title: str, lines: tuple[str, ...]) -> None:
    """打印一个带标题的详情分组。"""
    print(f"{title}：")
    if not lines:
        print("- 无")
        return
    for line in lines:
        print(f"- {line}")


def _readiness_status_label(status: str) -> str:
    """把 readiness 状态转换成 CLI 展示标签。"""
    if status == "ok":
        return "[OK]"
    if status == "missing":
        return "[缺失]"
    return "[未知]"


def _run_recorder(args: argparse.Namespace) -> int:
    """启动坐标记录工具。"""
    from game_automation.platform.desktop.adapters import (
        PyAutoGuiPixelColorReader,
        PyAutoGuiPointerPositionReader,
        TerminalKeyStateReader,
    )
    from game_automation.portable.tools.coordinate_recorder import CoordinateRecorder

    key_reader = None
    try:
        key_reader = TerminalKeyStateReader()
        recorder = CoordinateRecorder(
            pointer_reader=PyAutoGuiPointerPositionReader(),
            key_reader=key_reader,
            color_reader=PyAutoGuiPixelColorReader(),
            display_interval_seconds=args.display_interval,
            poll_interval_seconds=args.poll_interval,
        )
        recorder.run()
    except RuntimeError as exc:
        print(f"coordinate recorder setup failed: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"coordinate recorder configuration failed: {exc}", file=sys.stderr)
        return 2
    finally:
        if key_reader is not None:
            key_reader.close()
    return 0


def _run_ui(args: argparse.Namespace) -> int:
    """启动本地控制 UI。"""
    from game_automation.platform.local_desktop.entrypoints.local_ui import serve_local_control_ui

    return serve_local_control_ui(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="star", description="Game automation toolkit.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List available scripts.")

    details_parser = subparsers.add_parser("details", help="Show a named script's steps and dependencies.")
    details_parser.add_argument("name", help="Script name to inspect.")

    run_parser = subparsers.add_parser("run", help="Run a named script.")
    run_parser.add_argument("name", help="Script name to run.")
    mode = run_parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Print planned operations without real mouse.")
    mode.add_argument("--macos", action="store_true", help="Run with macOS adapter (default).")
    run_parser.add_argument(
        "--dry-run-color",
        default="#000000",
        help="Fixed #RRGGBB screen color used when dry-running color conditions.",
    )
    run_parser.add_argument(
        "--dry-run-image",
        action="append",
        default=[],
        help="Template path treated as found when dry-running image conditions. Can be repeated.",
    )
    run_parser.add_argument(
        "--dry-run-script-images",
        action="store_true",
        help="Treat resolved script image dependencies as found when dry-running.",
    )
    run_parser.add_argument(
        "--dry-run-screen-state",
        default="未知",
        help="Fixed screen state used when dry-running screen-state conditions.",
    )

    recorder_parser = subparsers.add_parser("recorder", help="Record screen coordinates.")
    recorder_parser.add_argument("--display-interval", type=float, default=1.0, help="Seconds between coordinate prints.")
    recorder_parser.add_argument("--poll-interval", type=float, default=0.05, help="Seconds between keyboard polls.")

    ui_parser = subparsers.add_parser("ui", help="Start the local control UI.")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Host address for the local UI server.")
    ui_parser.add_argument("--port", type=int, default=8765, help="Port for the local UI server.")
    ui_parser.add_argument("--no-open", action="store_true", help="Do not open a browser window after starting.")

    args = parser.parse_args(argv)

    if args.command == "list":
        return _run_list()
    elif args.command == "details":
        return _run_details(args)
    elif args.command == "run":
        return _run_script(args)
    elif args.command == "recorder":
        return _run_recorder(args)
    elif args.command == "ui":
        return _run_ui(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
