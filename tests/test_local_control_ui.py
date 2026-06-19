"""验证本地控制 UI 的 HTTP entrypoint。

这些测试通过真实本地 HTTP server 请求公开接口，确保 UI adapter 只负责 HTTP
转换，并把行为委托给 application 层。
"""

from __future__ import annotations

import http.client
import json
import threading

from game_automation.portable.application.local_control import ControlResult, ScriptRunStatus
from game_automation.platform.local_desktop.entrypoints.local_ui import create_local_control_server


def test_local_ui_lists_scripts_over_http() -> None:
    """验证 UI HTTP 接口可以返回脚本列表。"""
    server = create_local_control_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/scripts")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert "conditional-color-demo" in payload["scripts"]
    assert "wait-until-color-demo" in payload["scripts"]


def test_local_ui_serves_control_page() -> None:
    """验证根路径返回可操作的控制页面。"""
    server = create_local_control_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        html = _request_text(server.server_address, "GET", "/")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert "<title>Star 控制台</title>" in html
    assert 'id="script-select"' in html
    assert 'id="dry-run-enabled" type="checkbox" checked' in html
    assert 'id="run-script"' in html
    assert 'id="stop-script"' in html
    assert 'id="image-asset-select"' in html
    assert 'id="image-confidence"' in html
    assert 'id="click-image"' in html
    assert 'id="capture-screen"' in html
    assert 'id="debug-screenshot"' in html
    assert 'id="run-tests"' in html
    assert "运行测试" in html
    assert "查找并点击图片" in html
    assert "截屏诊断" in html


def test_local_ui_lists_image_assets_over_http() -> None:
    """验证 UI HTTP 接口可以返回图片资源列表。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/image-assets")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert payload == {
        "asset_folder": "assets",
        "assets": ["start.png", "confirm.webp"],
    }


def test_local_ui_runs_script_over_http() -> None:
    """验证 UI HTTP 接口把后台运行请求委托给 application。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/run-script",
            {
                "name": "conditional-color-demo",
                "dry_run": True,
                "dry_run_color": "#102030",
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.start_requests == [
        {
            "name": "conditional-color-demo",
            "dry_run": True,
            "dry_run_color": "#102030",
        }
    ]
    assert payload == {
        "running": True,
        "exit_code": None,
        "stdout": "started\n",
        "stderr": "",
    }


def test_local_ui_gets_script_run_status_over_http() -> None:
    """验证 UI HTTP 接口可以查询后台脚本状态。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/script-run")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.status_requests == 1
    assert payload == {
        "running": False,
        "exit_code": 0,
        "stdout": "done\n",
        "stderr": "",
    }


def test_local_ui_stops_script_run_over_http() -> None:
    """验证 UI HTTP 接口可以请求停止后台脚本。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "POST", "/api/stop-script", {})
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.stop_requests == 1
    assert payload == {
        "running": True,
        "exit_code": None,
        "stdout": "stopping\n",
        "stderr": "",
    }


def test_local_ui_clicks_image_asset_over_http() -> None:
    """验证 UI HTTP 接口把图片点击请求委托给 application。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/click-image",
            {
                "asset": "start.png",
                "dry_run": True,
                "min_confidence": 0.7,
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.image_click_requests == [
        {
            "asset": "start.png",
            "dry_run": True,
            "min_confidence": 0.7,
        }
    ]
    assert payload == {
        "exit_code": 0,
        "stdout": "click Point(x=0, y=0)\n",
        "stderr": "",
    }


def test_local_ui_rejects_non_numeric_image_confidence_over_http() -> None:
    """验证 UI HTTP 接口拒绝非数字图片置信度。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/click-image",
            {
                "asset": "start.png",
                "dry_run": True,
                "min_confidence": "bad",
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.image_click_requests == []
    assert payload == {
        "exit_code": 2,
        "stdout": "",
        "stderr": "invalid image click request: min_confidence must be a number\n",
    }


def test_local_ui_captures_screen_over_http() -> None:
    """验证 UI HTTP 接口把截屏诊断请求委托给 application。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/capture-screen",
            {},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.capture_requests == 1
    assert payload == {
        "exit_code": 0,
        "stdout": "saved screenshot: /tmp/latest-screen.png\n",
        "stderr": "",
        "screenshot_path": "/tmp/latest-screen.png",
        "screenshot_url": "/api/debug-screenshot?version=1",
    }


def test_local_ui_runs_tests_over_http() -> None:
    """验证 UI HTTP 接口可以触发固定测试任务。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/run-tests",
            {"task": "all"},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.test_requests == ["all"]
    assert payload == {
        "exit_code": 0,
        "stdout": "109 passed\n",
        "stderr": "",
    }


class FakeControlApplication:
    def __init__(self) -> None:
        """初始化 fake application 的请求记录。"""
        self.start_requests: list[dict[str, object]] = []
        self.status_requests = 0
        self.stop_requests = 0
        self.test_requests: list[str] = []
        self.image_click_requests: list[dict[str, object]] = []
        self.capture_requests = 0

    def list_scripts(self) -> tuple[str, ...]:
        return ("conditional-color-demo",)

    def image_asset_folder_label(self) -> str:
        """返回 fake 图片目录展示名。"""
        return "assets"

    def list_image_assets(self) -> tuple[str, ...]:
        """返回 fake 图片资源列表。"""
        return ("start.png", "confirm.webp")

    def start_named_script(self, name: str, *, dry_run: bool, dry_run_color: str) -> ScriptRunStatus:
        """记录 fake 后台脚本启动请求。"""
        self.start_requests.append(
            {
                "name": name,
                "dry_run": dry_run,
                "dry_run_color": dry_run_color,
            }
        )
        return ScriptRunStatus(running=True, stdout="started\n")

    def current_script_run(self) -> ScriptRunStatus:
        """记录 fake 后台脚本状态查询。"""
        self.status_requests += 1
        return ScriptRunStatus(running=False, exit_code=0, stdout="done\n")

    def stop_running_script(self) -> ScriptRunStatus:
        """记录 fake 后台脚本停止请求。"""
        self.stop_requests += 1
        return ScriptRunStatus(running=True, stdout="stopping\n")

    def run_tests(self, task_name: str = "all") -> ControlResult:
        self.test_requests.append(task_name)
        return ControlResult(exit_code=0, stdout="109 passed\n", stderr="")

    def click_image_asset(
        self,
        asset_name: str,
        *,
        dry_run: bool,
        min_confidence: float = 0.8,
    ) -> ControlResult:
        """记录 fake 图片点击请求。"""
        self.image_click_requests.append(
            {
                "asset": asset_name,
                "dry_run": dry_run,
                "min_confidence": min_confidence,
            }
        )
        return ControlResult(exit_code=0, stdout="click Point(x=0, y=0)\n", stderr="")

    def capture_screen_screenshot(self) -> ControlResult:
        """记录 fake 截屏诊断请求。"""
        self.capture_requests += 1
        return ControlResult(
            exit_code=0,
            stdout="saved screenshot: /tmp/latest-screen.png\n",
            stderr="",
            screenshot_path="/tmp/latest-screen.png",
        )


def _request_json(address, method: str, path: str, body: dict[str, object] | None = None) -> dict[str, object]:
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    try:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Content-Type": "application/json"} if body is not None else {}
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        data = response.read().decode("utf-8")
    finally:
        connection.close()
    assert response.status == 200
    return json.loads(data)


def _request_text(address, method: str, path: str) -> str:
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        data = response.read().decode("utf-8")
    finally:
        connection.close()
    assert response.status == 200
    return data
