"""提供视觉靶场的独立 HTTP 入口和静态资源 adapter。

本 module 负责参数解析、HTTP/JSON 转换和浏览器启动；它不实现状态转换规则，
也不导入 Star 的脚本 domain、runner、application 或平台 adapter。
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import webbrowser

from star_visual_lab.scenario import (
    SUPPORTED_MODES,
    ScenarioActionError,
    ScenarioEvent,
    ScenarioSnapshot,
    TaskFlowScenario,
)


STATIC_ROOT = Path(__file__).with_name("static")
CONTENT_TYPES = {
    ".css": "text/css; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


def serve_visual_lab(
    *,
    host: str,
    port: int,
    open_browser: bool,
    mode: str,
    loading_delay_seconds: float | None,
) -> int:
    """启动视觉靶场并阻塞到用户中断。"""
    scenario = TaskFlowScenario(
        mode=mode,
        loading_delay_seconds=loading_delay_seconds,
    )
    server = create_visual_lab_server(host=host, port=port, scenario=scenario)
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"Star visual lab: {url}")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


def create_visual_lab_server(
    *,
    host: str,
    port: int,
    scenario: TaskFlowScenario | None = None,
) -> ThreadingHTTPServer:
    """创建可由入口或测试控制生命周期的靶场 server。"""
    lab_scenario = scenario if scenario is not None else TaskFlowScenario()

    class VisualLabHandler(BaseHTTPRequestHandler):
        """把视觉靶场 HTTP 请求映射到状态机和静态资源。"""

        def do_GET(self) -> None:
            """处理目标页面、静态资源和真值读取。"""
            path = urlparse(self.path).path
            if path == "/":
                self._send_static("index.html")
                return
            if path.startswith("/static/"):
                self._send_static(path.removeprefix("/static/"))
                return
            if path == "/api/state":
                self._send_json(_snapshot_payload(lab_scenario.snapshot()))
                return
            if path == "/api/events":
                self._send_json({"events": _events_payload(lab_scenario.events())})
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            """处理目标页面动作和测试重置请求。"""
            try:
                payload = self._read_json()
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            if self.path == "/api/action":
                action = str(payload.get("action", ""))
                try:
                    snapshot = lab_scenario.perform(action)
                except ScenarioActionError as exc:
                    self._send_json(
                        {
                            "error": str(exc),
                            "state": _snapshot_payload(lab_scenario.snapshot()),
                        },
                        status=HTTPStatus.CONFLICT,
                    )
                    return
                self._send_json(_snapshot_payload(snapshot))
                return
            if self.path == "/api/reset":
                try:
                    snapshot = lab_scenario.reset(
                        mode=str(payload.get("mode", "normal")),
                        loading_delay_seconds=_optional_number(
                            payload.get("loading_delay_seconds")
                        ),
                    )
                except (TypeError, ValueError) as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(_snapshot_payload(snapshot))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args: object) -> None:
            """保持靶场和自动化测试输出安静。"""

        def _read_json(self) -> dict[str, Any]:
            """读取请求体并要求顶层为 JSON object。"""
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ValueError("invalid visual lab json request") from exc
            if not isinstance(payload, dict):
                raise ValueError("visual lab json request must be an object")
            return payload

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            """发送 UTF-8 JSON 响应。"""
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, relative_path: str) -> None:
            """从靶场静态目录读取并发送允许的资源。"""
            try:
                path = _resolve_static_path(relative_path)
                body = path.read_bytes()
            except (OSError, ValueError):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self.send_response(HTTPStatus.OK)
            self.send_header(
                "Content-Type",
                CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream"),
            )
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), VisualLabHandler)


def main(argv: list[str] | None = None) -> int:
    """解析 star-lab 参数并启动独立靶场服务。"""
    parser = argparse.ArgumentParser(
        prog="star-lab",
        description="Run a deterministic local visual automation target.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Local bind host.")
    parser.add_argument("--port", type=int, default=8770, help="Local bind port.")
    parser.add_argument("--no-open", action="store_true", help="Do not open a browser window.")
    parser.add_argument(
        "--mode",
        choices=SUPPORTED_MODES,
        default="normal",
        help="Deterministic scenario mode.",
    )
    parser.add_argument(
        "--loading-delay",
        type=float,
        default=None,
        help="Override loading delay in seconds.",
    )
    args = parser.parse_args(argv)
    return serve_visual_lab(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        mode=args.mode,
        loading_delay_seconds=args.loading_delay,
    )


def _snapshot_payload(snapshot: ScenarioSnapshot) -> dict[str, Any]:
    """把状态快照转换成稳定 JSON payload。"""
    payload = asdict(snapshot)
    payload["available_actions"] = list(snapshot.available_actions)
    return payload


def _events_payload(events: tuple[ScenarioEvent, ...]) -> list[dict[str, Any]]:
    """把事件序列转换成稳定 JSON payload。"""
    return [asdict(event) for event in events]


def _optional_number(value: Any) -> float | None:
    """把可选 JSON 数字转换成浮点数并拒绝布尔值。"""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("loading_delay_seconds must be a number")
    return float(value)


def _resolve_static_path(relative_path: str) -> Path:
    """解析静态资源路径并阻止离开靶场目录。"""
    path = (STATIC_ROOT / relative_path).resolve()
    path.relative_to(STATIC_ROOT.resolve())
    if not path.is_file():
        raise ValueError(f"unknown visual lab asset: {relative_path}")
    return path


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
