"""把本地控制台的 HTTP 请求映射到脚本运行用例。

本 module 提供静态页面、脚本列表与详情、后台运行状态和运行/停止接口；
它不解释脚本步骤、不创建平台 adapter，也不承载开发调试工具。
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from game_automation.platform.local_desktop.composition import build_local_control_application
from game_automation.platform.local_desktop.entrypoints.local_ui_assets import read_ui_asset
from game_automation.portable.application.local_control import LocalControlApplication
from game_automation.portable.engine.run_events import script_run_event_to_payload


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
    """创建本地控制台 HTTP server，供 CLI 或测试控制生命周期。"""
    control_app = app if app is not None else build_local_control_application()

    class LocalControlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """读取控制页面、脚本信息和当前运行状态。"""
            parsed_url = urlparse(self.path)
            path = parsed_url.path
            if path == "/":
                self._send_ui_asset("index.html")
            elif path.startswith("/static/"):
                self._send_ui_asset(path.removeprefix("/static/"))
            elif path == "/api/scripts":
                self._send_json({
                    "scripts": list(control_app.list_scripts()),
                    "script_config_errors": _script_config_errors_to_payload(
                        control_app.list_script_config_errors()
                    ),
                })
            elif path == "/api/script-details":
                name = parse_qs(parsed_url.query).get("name", [""])[0]
                self._send_json(_script_details_to_payload(control_app.describe_script(name)))
            elif path == "/api/screen-state-names":
                self._send_json({"states": list(control_app.list_screen_state_names())})
            elif path == "/api/script-run":
                self._send_json(_status_to_payload(control_app.current_script_run()))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            """请求后台运行或停止当前脚本。"""
            if self.path == "/api/run-script":
                try:
                    payload = self._read_json()
                except (ValueError, UnicodeDecodeError):
                    self._send_json({"error": "请求必须是 JSON 对象"}, HTTPStatus.BAD_REQUEST)
                    return
                status = control_app.start_named_script(
                    str(payload.get("name", "")),
                    dry_run=bool(payload.get("dry_run", True)),
                    dry_run_color=str(payload.get("dry_run_color", "#000000")),
                    dry_run_screen_state=str(payload.get("dry_run_screen_state", "未知")),
                    dry_run_images=_parse_dry_run_images(payload),
                )
                self._send_json(_status_to_payload(status))
            elif self.path == "/api/stop-script":
                self._send_json(_status_to_payload(control_app.stop_running_script()))
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: Any) -> None:
            """禁止 CLI 和测试输出默认 HTTP 访问日志。"""

        def _read_json(self) -> dict[str, object]:
            """读取 JSON 对象并拒绝无效请求，避免误启动默认脚本。"""
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            parsed = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("request body must be an object")
            return parsed

        def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
            """发送不缓存的 JSON 响应。"""
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_ui_asset(self, asset_name: str) -> None:
            """发送本地控制台的白名单静态资源。"""
            try:
                asset = read_ui_asset(asset_name)
            except FileNotFoundError:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", asset.content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(asset.body)))
            self.end_headers()
            self.wfile.write(asset.body)

    return ThreadingHTTPServer((host, port), LocalControlHandler)


def _status_to_payload(status) -> dict[str, object]:
    """把后台脚本运行状态转换成 HTTP JSON payload。"""
    return {
        "running": status.running,
        "exit_code": status.exit_code,
        "finish_reason": status.finish_reason,
        "stdout": status.stdout,
        "stderr": status.stderr,
        "events": [script_run_event_to_payload(event) for event in status.events],
    }


def _script_details_to_payload(details) -> dict[str, object]:
    """把脚本详情转换成 HTTP JSON payload。"""
    return {
        "exit_code": details.exit_code,
        "name": details.name,
        "steps": list(details.steps),
        "dependencies": list(details.dependencies),
        "state_dependencies": list(details.state_dependencies),
        "point_dependencies": list(details.point_dependencies),
        "state_waits": list(details.state_waits),
        "state_decisions": [
            {
                "state": state,
                "matched_steps": list(matched_steps),
                "unmatched_steps": list(unmatched_steps),
            }
            for state, matched_steps, unmatched_steps in details.state_decisions
        ],
        "image_dependencies": list(details.image_dependencies),
        "readiness": [
            {"label": label, "status": status, "message": message}
            for label, status, message in details.readiness
        ],
        "stderr": details.stderr,
    }


def _script_config_errors_to_payload(errors) -> list[dict[str, str]]:
    """把文件脚本配置错误转换成 HTTP JSON payload。"""
    return [{"file": error.file, "message": error.message} for error in errors]


def _parse_dry_run_images(payload: dict[str, object]) -> tuple[str, ...]:
    """把 HTTP payload 中的 dry-run 图片列表解析为字符串 tuple。"""
    value = payload.get("dry_run_images", ())
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)
