"""为原生桌面壳提供本地标准输入输出协议及可回收的后台会话。

本 module 只映射准备与运行用例，不开启 HTTP、导入 GUI 或解释脚本步骤；
PNG 通过独占临时文件交付，协议输出固定写入宿主传入的原始流。
"""

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import signal
import sys
import tempfile
from typing import Callable, TextIO

from game_automation.portable.domain.geometry import Point, Rect


class WorkspaceLock:
    def __init__(self, workspace: Path) -> None:
        """将单实例锁绑定到工作区，不删除其他进程的锁文件。"""
        self.path = workspace / ".star" / "desktop.lock"
        self._file = None

    def __enter__(self):
        """通过内核文件锁拒绝同一工作区的第二个后台。"""
        import fcntl
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+")
        try:
            fcntl.flock(self._file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self._file.close()
            self._file = None
            raise RuntimeError("this workspace already has a desktop backend") from exc
        return self

    def __exit__(self, *args) -> None:
        """关闭句柄释放锁，进程异常退出时也由内核回收。"""
        if self._file is not None:
            self._file.close()
            self._file = None


class DesktopBackend:
    def __init__(self, workspace: Path, *, preparation=None, control_factory: Callable | None = None) -> None:
        """装配独立准备服务，延迟加载执行服务并创建单帧缓存。"""
        self.workspace = workspace.resolve()
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")
        if preparation is None:
            from game_automation.platform.local_desktop.preparation_composition import build_preparation_service
            preparation = build_preparation_service(self.workspace)
        self.preparation = preparation
        self._control_factory = control_factory
        self._control_app = None
        self._cache = tempfile.TemporaryDirectory(prefix="star-desktop-")
        self._frame_path: Path | None = None
        self.stopping = False
        self._closed = False

    def _control(self):
        """首次进入运行功能时才加载 catalog 和执行用例。"""
        if self._control_app is None:
            if self._control_factory is not None:
                self._control_app = self._control_factory()
            else:
                from game_automation.platform.local_desktop.composition import build_local_control_application
                self._control_app = build_local_control_application(project_root=self.workspace, include_builtin_scripts=False)
        return self._control_app

    def dispatch(self, method: str, params: dict) -> dict:
        """串行处理壳请求，运行中不允许新的素材操作或重复启动。"""
        if self.stopping:
            raise RuntimeError("desktop backend is stopping")
        running = self._control_app is not None and self._control_app.current_script_run().running
        if running and (method.startswith("preparation.") or method in {"script.reload", "script.start"}):
            raise RuntimeError("a script is running; stop it before preparing materials or starting another")
        if method == "session.info":
            return {"protocol": 1, "workspace": str(self.workspace), "pid": os.getpid(), "process_group": os.getpgrp()}
        if method == "session.shutdown":
            self.stopping = True
            return {"stopping": True}
        if method == "preparation.windows":
            return {"windows": [asdict(window) for window in self.preparation.list_windows(_text(params, "application"))]}
        if method == "preparation.capture":
            if self._frame_path is not None:
                self._frame_path.unlink(missing_ok=True)
            frame = self.preparation.capture_window(_text(params, "application"), _text(params, "window_id"))
            self._frame_path = Path(self._cache.name) / f"{frame.id}.png"
            self._frame_path.write_bytes(frame.image.png)
            return {"id": frame.id, "window": asdict(frame.window), "captured_at": frame.captured_at,
                    "image": {"path": str(self._frame_path), "width": frame.image.width, "height": frame.image.height}}
        if method == "preparation.point":
            relative, screen = self.preparation.locate_point(
                _text(params, "frame_id"), Point(_integer(params, "x"), _integer(params, "y")))
            return {"window_relative": asdict(relative), "screen": asdict(screen)}
        if method == "preparation.crop":
            region = params.get("region")
            if not isinstance(region, dict):
                raise ValueError("region must be an object")
            name = _text(params, "name")
            image = self.preparation.save_crop(
                _text(params, "frame_id"), Rect(*(_integer(region, key) for key in ("left", "top", "width", "height"))), name)
            return {"image": image, "resources": {"images": {name: image}}}
        if method in {"script.list", "script.reload"}:
            if method == "script.reload":
                self._control_app = None
            app = self._control()
            return {"scripts": list(app.list_scripts()),
                    "errors": [asdict(error) for error in app.list_script_config_errors()]}
        if method == "script.details":
            return asdict(self._control().describe_script(_text(params, "name")))
        if method == "script.start":
            name = _text(params, "name")
            dry_run = params.get("dry_run", True)
            if type(dry_run) is not bool:
                raise ValueError("dry_run must be a boolean")
            app = self._control()
            details = app.describe_script(name)
            return _run_status(app.start_named_script(
                name, dry_run=dry_run, dry_run_color=_text(params, "dry_run_color", "#000000"),
                dry_run_screen_state=_text(params, "dry_run_screen_state", "未知"),
                dry_run_images=details.image_dependencies if dry_run else (),
            ))
        if method == "script.status":
            if self._control_app is None:
                return {"running": False, "finish_reason": "idle", "stdout": "", "stderr": "", "exit_code": None}
            return _run_status(self._control_app.current_script_run())
        if method == "script.stop":
            return _run_status(self._control().stop_running_script())
        raise KeyError(f"unknown desktop method: {method}")

    def close(self, timeout: float = 5) -> bool:
        """请求停止并等待执行线程回收，释放当前帧和临时目录。"""
        if self._closed:
            return True
        self.stopping = True
        stopped = True
        if self._control_app is not None:
            self._control_app.stop_running_script()
            stopped = self._control_app.wait_for_script_stop(timeout)
        self._cache.cleanup()
        self._closed = True
        return stopped


def _run_status(status) -> dict:
    """限制跨进程日志大小，不发送重复的截图或完整事件树。"""
    return {"running": status.running, "exit_code": status.exit_code, "finish_reason": status.finish_reason,
            "stdout": status.stdout[-65536:], "stderr": status.stderr[-8192:]}


def _text(params: dict, key: str, default=None) -> str:
    """校验必需文本字段，避免隐式启动默认操作。"""
    value = params.get(key, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be non-empty text")
    return value.strip()


def _integer(params: dict, key: str) -> int:
    """校验像素字段为整数而非布尔值或浮点数。"""
    value = params.get(key)
    if type(value) is not int:
        raise ValueError(f"{key} must be an integer")
    return value


def run_stdio(session: DesktopBackend, source: TextIO, output: TextIO, errors: TextIO) -> int:
    """处理 JSON-RPC 行协议；关闭、管道 EOF 和中断统一回收后台。"""
    exit_code = 0
    try:
        while not session.stopping:
            line = source.readline(1048577)
            if not line:
                break
            request_id = None
            try:
                if len(line) > 1048576:
                    raise ValueError("desktop request is too large")
                request = json.loads(line)
                if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                    raise ValueError("request must be a JSON-RPC 2.0 object")
                request_id = request.get("id")
                if type(request_id) not in (int, str):
                    raise ValueError("request id must be an integer or string")
                method = _text(request, "method")
                params = request.get("params", {})
                if not isinstance(params, dict):
                    raise ValueError("params must be an object")
                reply = {"jsonrpc": "2.0", "id": request_id, "result": session.dispatch(method, params)}
            except Exception as exc:
                code = -32700 if isinstance(exc, json.JSONDecodeError) else -32602 if isinstance(exc, (ValueError, TypeError)) else -32601 if isinstance(exc, KeyError) else -32000
                reply = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": str(exc)}}
            # 不使用 print/sys.stdout：运行线程可能临时重定向全局标准输出。
            output.write(json.dumps(reply, ensure_ascii=False, allow_nan=False) + "\n")
            output.flush()
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        if not session.close():
            errors.write("desktop shutdown timed out while waiting for the input adapter\n")
            errors.flush()
            exit_code = 1
    return exit_code


def main(argv: list[str] | None = None) -> int:
    """启动被原生壳监督的独立进程，绑定工作区锁与终止信号。"""
    parser = argparse.ArgumentParser(description="Internal Star desktop backend")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args(argv)

    def interrupt(signum, frame):
        """将宿主终止请求送入统一退出路径。"""
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    if os.getpgrp() != os.getpid():
        os.setsid()
    root = Path(args.workspace).expanduser().resolve()
    if not root.is_dir():
        print("workspace must be an existing directory", file=sys.stderr)
        return 2
    try:
        with WorkspaceLock(root):
            return run_stdio(DesktopBackend(root), sys.stdin, sys.stdout, sys.stderr)
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
