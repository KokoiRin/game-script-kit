"""本地控制 UI 的 HTTP 入口 adapter。

本 module 负责把浏览器页面和 JSON 请求转换为 application 调用；它不直接运行
脚本、不导入平台自动化 adapter，也不提供通用命令执行能力。
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from game_automation.platform.local_desktop.composition import build_local_control_application
from game_automation.platform.local_desktop.entrypoints.local_ui_assets import read_ui_asset
from game_automation.portable.application.local_control import LocalControlApplication


def serve_local_control_ui(*, host: str, port: int, open_browser: bool) -> int:
    """启动本地控制 UI，并阻塞直到用户中断。"""
    server = create_local_control_server(host=host, port=port)
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"Star control UI: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def create_local_control_server(
    *,
    host: str,
    port: int,
    app: LocalControlApplication | None = None,
) -> ThreadingHTTPServer:
    """创建本地 UI HTTP server，供 CLI 或测试控制生命周期。"""
    control_app = app if app is not None else build_local_control_application()
    latest_screenshot_path = ""
    screenshot_version = 0

    class LocalControlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """处理控制页面、脚本列表和图片资源列表读取请求。"""
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            if path == "/":
                self._send_ui_asset("index.html")
                return
            if path.startswith("/static/"):
                self._send_ui_asset(path.removeprefix("/static/"))
                return
            if path == "/api/scripts":
                self._send_json({"scripts": list(control_app.list_scripts())})
                return
            if path == "/api/script-details":
                query = parse_qs(parsed_url.query)
                name = query.get("name", [""])[0]
                self._send_json(_script_details_to_payload(control_app.describe_script(name)))
                return
            if path == "/api/image-assets":
                self._send_json(
                    {
                        "asset_folder": control_app.image_asset_folder_label(),
                        "assets": list(control_app.list_image_assets()),
                    }
                )
                return
            if path == "/api/screen-state-names":
                self._send_json({"states": list(control_app.list_screen_state_names())})
                return
            if path == "/api/script-run":
                self._send_json(_status_to_payload(control_app.current_script_run()))
                return
            if path == "/api/screen-state-probe":
                self._send_json(_probe_status_to_payload(control_app.current_screen_state_probe()))
                return
            if path == "/api/debug-screenshot":
                self._send_png_file(Path(latest_screenshot_path))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            """处理脚本运行、图片点击和固定测试任务请求。"""
            nonlocal latest_screenshot_path, screenshot_version
            if self.path == "/api/run-script":
                payload = self._read_json()
                status = control_app.start_named_script(
                    str(payload.get("name", "")),
                    dry_run=bool(payload.get("dry_run", True)),
                    dry_run_color=str(payload.get("dry_run_color", "#000000")),
                    dry_run_screen_state=str(payload.get("dry_run_screen_state", "未知")),
                    dry_run_images=_parse_dry_run_images(payload),
                )
                self._send_json(_status_to_payload(status))
                return
            if self.path == "/api/stop-script":
                status = control_app.stop_running_script()
                self._send_json(_status_to_payload(status))
                return
            if self.path == "/api/start-screen-state-probe":
                payload = self._read_json()
                min_confidence = _parse_min_confidence(payload)
                interval_seconds = _parse_interval_seconds(payload)
                if min_confidence is None or interval_seconds is None:
                    self._send_json(
                        {
                            "running": False,
                            "current_state": "未知",
                            "exit_code": 2,
                            "stdout": "",
                            "stderr": "invalid screen state probe request: min_confidence and interval_seconds must be numbers\n",
                        }
                    )
                    return
                status = control_app.start_screen_state_probe(
                    min_confidence=min_confidence,
                    interval_seconds=interval_seconds,
                )
                self._send_json(_probe_status_to_payload(status))
                return
            if self.path == "/api/stop-screen-state-probe":
                status = control_app.stop_screen_state_probe()
                self._send_json(_probe_status_to_payload(status))
                return
            if self.path == "/api/click-image":
                payload = self._read_json()
                min_confidence = _parse_min_confidence(payload)
                if min_confidence is None:
                    self._send_json(
                        {
                            "exit_code": 2,
                            "stdout": "",
                            "stderr": "invalid image click request: min_confidence must be a number\n",
                        }
                    )
                    return
                result = control_app.click_image_asset(
                    str(payload.get("asset", "")),
                    dry_run=bool(payload.get("dry_run", True)),
                    min_confidence=min_confidence,
                )
                self._send_json(_result_to_payload(result))
                return
            if self.path == "/api/capture-screen":
                result = control_app.capture_screen_screenshot()
                payload = _result_to_payload(result)
                if result.screenshot_path:
                    screenshot_version += 1
                    latest_screenshot_path = result.screenshot_path
                    payload["screenshot_url"] = f"/api/debug-screenshot?version={screenshot_version}"
                self._send_json(payload)
                return
            if self.path == "/api/capture-region-diagnostics":
                result = control_app.capture_screen_region_diagnostics()
                payload = _result_to_payload(result)
                if result.screenshot_path:
                    screenshot_version += 1
                    latest_screenshot_path = result.screenshot_path
                    payload["screenshot_url"] = f"/api/debug-screenshot?version={screenshot_version}"
                self._send_json(payload)
                return
            if self.path == "/api/run-tests":
                payload = self._read_json()
                result = control_app.run_tests(str(payload.get("task", "all")))
                self._send_json(_result_to_payload(result))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            """禁止测试和 CLI 输出默认 HTTP 访问日志。"""

        def _read_json(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            body = self.rfile.read(length).decode("utf-8")
            parsed = json.loads(body)
            if not isinstance(parsed, dict):
                return {}
            return parsed

        def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_png_file(self, path: Path) -> None:
            """把最近保存的诊断截图作为 PNG 响应给浏览器。"""
            if not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_ui_asset(self, asset_name: str) -> None:
            """发送本地控制 UI 的白名单静态资源。"""
            try:
                asset = read_ui_asset(asset_name)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = asset.body
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", asset.content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), LocalControlHandler)


def _result_to_payload(result) -> dict[str, object]:
    """把 application 结果转换成 HTTP JSON payload。"""
    payload = {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if result.screenshot_path:
        payload["screenshot_path"] = result.screenshot_path
    return payload


def _status_to_payload(status) -> dict[str, object]:
    """把后台脚本运行状态转换成 HTTP JSON payload。"""
    return {
        "running": status.running,
        "exit_code": status.exit_code,
        "stdout": status.stdout,
        "stderr": status.stderr,
    }


def _script_details_to_payload(details) -> dict[str, object]:
    """把脚本详情转换成 HTTP JSON payload。"""
    return {
        "exit_code": details.exit_code,
        "name": details.name,
        "steps": list(details.steps),
        "dependencies": list(details.dependencies),
        "state_dependencies": list(details.state_dependencies),
        "image_dependencies": list(details.image_dependencies),
        "readiness": [
            {"label": label, "status": status, "message": message}
            for label, status, message in details.readiness
        ],
        "stderr": details.stderr,
    }


def _probe_status_to_payload(status) -> dict[str, object]:
    """把后台界面探测状态转换成 HTTP JSON payload。"""
    return {
        "running": status.running,
        "current_state": status.current_state,
        "exit_code": status.exit_code,
        "stdout": status.stdout,
        "stderr": status.stderr,
    }


def _parse_min_confidence(payload: dict[str, object]) -> float | None:
    """把 HTTP payload 中的图片匹配置信度解析为数字。"""
    try:
        return float(payload.get("min_confidence", 0.8))
    except (TypeError, ValueError):
        return None


def _parse_interval_seconds(payload: dict[str, object]) -> float | None:
    """把 HTTP payload 中的界面探测间隔解析为数字。"""
    try:
        return float(payload.get("interval_seconds", 1.0))
    except (TypeError, ValueError):
        return None


def _parse_dry_run_images(payload: dict[str, object]) -> tuple[str, ...]:
    """把 HTTP payload 中的 dry-run 图片列表解析为字符串 tuple。"""
    value = payload.get("dry_run_images", ())
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)
