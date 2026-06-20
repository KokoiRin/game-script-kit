"""star 命令行入口。

本 module 负责解析命令行参数、查找内置脚本并打印用户可见结果；脚本运行和
本地 UI 委托应用/入口编排层，recorder 子命令保留终端工具组装但不解释脚本步骤。
"""

from __future__ import annotations

import argparse
import json
import sys

from game_automation.platform.local_desktop.composition import (
    build_local_control_application,
    run_script_on_local_desktop,
)
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
    dry_run_screen_state_error = _validate_dry_run_screen_state_args(args)
    if dry_run_screen_state_error != 0:
        return dry_run_screen_state_error
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

    dry_run_screen_state_result = _resolve_dry_run_screen_state(args)
    if dry_run_screen_state_result[0] != 0:
        return dry_run_screen_state_result[0]
    dry_run_screen_state = dry_run_screen_state_result[1]

    result = run_script_on_local_desktop(
        script,
        dry_run=args.dry_run,
        dry_run_color=args.dry_run_color,
        dry_run_images=dry_run_images,
        dry_run_screen_state=dry_run_screen_state,
    )
    if result.error_message is not None:
        print(result.error_message, file=sys.stderr)
    return result.exit_code


def _validate_dry_run_screen_state_args(args: argparse.Namespace) -> int:
    """校验 CLI dry-run 状态来源参数是否自洽。"""
    if args.dry_run_probed_screen_state and not args.dry_run:
        print("--dry-run-probed-screen-state requires --dry-run", file=sys.stderr)
        return 2
    if args.dry_run_probed_screen_state and args.dry_run_screen_state is not None:
        print("--dry-run-probed-screen-state conflicts with --dry-run-screen-state", file=sys.stderr)
        return 2
    return 0


def _resolve_dry_run_screen_state(args: argparse.Namespace) -> tuple[int, str]:
    """解析 CLI dry-run 状态来源。"""
    if not args.dry_run_probed_screen_state:
        return (0, "未知" if args.dry_run_screen_state is None else args.dry_run_screen_state)
    try:
        result = build_local_control_application().probe_screen_state_once()
    except ValueError as exc:
        print(f"screen state probe configuration failed: {exc}", file=sys.stderr)
        return (2, "未知")
    except RuntimeError as exc:
        print(f"screen state probe failed: {exc}", file=sys.stderr)
        return (1, "未知")
    return (0, result.current_state)


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


def _run_probe_state(args: argparse.Namespace) -> int:
    """执行一轮本机界面状态探测。"""
    try:
        result = build_local_control_application().probe_screen_state_once(
            min_confidence=args.min_confidence,
        )
    except ValueError as exc:
        print(f"screen state probe configuration failed: {exc}", file=sys.stderr)
        return 2
    except RuntimeError as exc:
        print(f"screen state probe failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_screen_state_probe_json(result)
    else:
        _print_screen_state_probe_result(result)
    return 0


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


def _print_screen_state_probe_result(result) -> None:
    """把单次界面状态探测结果打印成 CLI 文本。"""
    print(f"当前状态：{result.current_state}")
    print(f"总耗时：{result.elapsed_ms:.2f}ms")
    print("候选：")
    if not result.candidates:
        print("- 无")
        return
    for candidate in result.candidates:
        print(f"- {_screen_state_candidate_line(candidate)}")


def _print_screen_state_probe_json(result) -> None:
    """把单次界面状态探测结果打印成 JSON。"""
    print(json.dumps(_screen_state_probe_payload(result), ensure_ascii=False))


def _screen_state_probe_payload(result) -> dict[str, object]:
    """把状态探测结果转换成机器可读 payload。"""
    return {
        "current_state": result.current_state,
        "known": result.known,
        "elapsed_ms": result.elapsed_ms,
        "candidates": [_screen_state_candidate_payload(candidate) for candidate in result.candidates],
    }


def _screen_state_candidate_payload(candidate) -> dict[str, object]:
    """把单个状态候选转换成机器可读 payload。"""
    return {
        "name": candidate.candidate.name,
        "search_name": candidate.candidate.search_name,
        "status": _candidate_status_value(candidate),
        "elapsed_ms": candidate.elapsed_ms,
        "confidence": candidate.confidence,
    }


def _screen_state_candidate_line(candidate) -> str:
    """把单个状态候选结果转换成一行 CLI 文本。"""
    name = candidate.candidate.name
    if candidate.candidate.search_name:
        name = f"{name} / {candidate.candidate.search_name}"
    confidence = "无" if candidate.confidence is None else f"{candidate.confidence:.3f}"
    return (
        f"{name}：{_candidate_status_label(candidate)}；"
        f"耗时 {candidate.elapsed_ms:.2f}ms；置信度 {confidence}"
    )


def _candidate_status_label(candidate) -> str:
    """把候选命中状态转换成 CLI 展示文本。"""
    if candidate.skipped:
        return "跳过"
    if candidate.found:
        return "命中"
    return "未命中"


def _candidate_status_value(candidate) -> str:
    """把候选命中状态转换成稳定枚举值。"""
    if candidate.skipped:
        return "skipped"
    if candidate.found:
        return "matched"
    return "missed"


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

    probe_parser = subparsers.add_parser("probe-state", help="Probe the current screen state once.")
    probe_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.8,
        help="Minimum image match confidence for this probe.",
    )
    probe_parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")

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
        default=None,
        help="Fixed screen state used when dry-running screen-state conditions.",
    )
    run_parser.add_argument(
        "--dry-run-probed-screen-state",
        action="store_true",
        help="Probe current screen state once and use it for dry-run screen-state conditions.",
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
    elif args.command == "probe-state":
        return _run_probe_state(args)
    elif args.command == "run":
        return _run_script(args)
    elif args.command == "recorder":
        return _run_recorder(args)
    elif args.command == "ui":
        return _run_ui(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
