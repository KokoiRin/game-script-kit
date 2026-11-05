"""启动 macOS 原生桌面应用。

本 module 只定位并启动 Swift 构建产物、传递后端环境及转发退出请求；
不启动浏览器、HTTP 服务或导入 Qt，也不执行脚本。
"""

import argparse
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys


def launch_desktop(*, workspace: Path | None = None, initial_tab: str = "prepare") -> int:
    """启动原生壳并等待其生命周期结束，终端中断时先请求有序退出。"""
    if platform.system() != "Darwin":
        raise RuntimeError("Star 原生桌面应用需要 macOS；云端可运行后台协议与核心测试。")
    root = Path(os.environ.get("STAR_SOURCE_ROOT", Path(__file__).resolve().parents[5]))
    configured = os.environ.get("STAR_DESKTOP_EXECUTABLE")
    candidates = [Path(configured)] if configured else [
        root / "native/StarDesktop/.build/debug/StarDesktop",
        root / "native/StarDesktop/.build/release/StarDesktop",
    ]
    executable = next((path for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)
    if executable is None:
        raise RuntimeError("尚未构建原生应用。请先运行：swift build --package-path native/StarDesktop")
    command = [str(executable), "--tab", initial_tab]
    if workspace is not None:
        command.extend(("--workspace", str(workspace)))
    environment = dict(os.environ, STAR_SOURCE_ROOT=str(root), STAR_PYTHON=sys.executable)
    child = subprocess.Popen(command, env=environment, start_new_session=True)
    try:
        return child.wait()
    except KeyboardInterrupt:
        child.send_signal(signal.SIGTERM)
        try:
            return child.wait(timeout=12)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            return 130


def main(argv: list[str] | None = None) -> int:
    """提供不依赖运行 CLI 导入链的桌面启动入口。"""
    parser = argparse.ArgumentParser(description="Star macOS native desktop")
    parser.add_argument("--workspace")
    parser.add_argument("--tab", choices=("prepare", "run"), default="prepare")
    args = parser.parse_args(argv)
    workspace = None if args.workspace is None else Path(args.workspace).expanduser().resolve()
    if workspace is not None and not workspace.is_dir():
        print("workspace must be an existing directory", file=sys.stderr)
        return 2
    try:
        return launch_desktop(workspace=workspace, initial_tab=args.tab)
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
