"""验证本地控制 UI 的 HTTP entrypoint。

这些测试通过真实本地 HTTP server 请求公开接口，确保 UI adapter 只负责 HTTP
转换，并把行为委托给 application 层。
"""

from __future__ import annotations

import http.client
import json
import threading

from game_automation.portable.application.local_control import (
    ControlResult,
    ScreenStateProbeStatus,
    ScriptDetailsResult,
    ScriptRunStatus,
)
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
    assert 'href="/static/control.css"' in html
    assert 'src="/static/control.js"' in html
    assert 'id="script-select"' in html
    assert 'id="script-details"' in html
    assert 'id="dry-run-enabled" type="checkbox" checked' in html
    assert 'id="dry-run-screen-state"' in html
    assert 'list="screen-state-suggestions"' in html
    assert 'id="screen-state-suggestions"' in html
    assert 'id="use-probed-screen-state"' in html
    assert 'id="run-script"' in html
    assert 'id="stop-script"' in html
    assert 'id="image-asset-select"' in html
    assert 'id="image-confidence"' in html
    assert 'id="click-image"' in html
    assert 'id="capture-screen"' in html
    assert 'id="capture-region-diagnostics"' in html
    assert 'id="debug-screenshot"' in html
    assert 'id="run-tests"' in html
    assert 'id="screen-state-tab"' in html
    assert 'id="start-screen-state-probe"' in html
    assert 'id="stop-screen-state-probe"' in html
    assert 'id="screen-state-interval"' in html
    assert 'id="screen-state-current"' in html
    assert 'id="screen-state-log"' in html
    assert "运行测试" in html
    assert "模拟状态" in html
    assert "查找并点击图片" in html
    assert "截屏诊断" in html
    assert "区域诊断" in html
    assert "界面探测" in html


def test_local_ui_serves_static_assets() -> None:
    """验证控制页面的 CSS 和 JS 会通过静态资源 endpoint 返回。"""
    server = create_local_control_server(host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        css = _request_text(server.server_address, "GET", "/static/control.css")
        script = _request_text(server.server_address, "GET", "/static/control.js")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert ".screen-state-toolbar" in css
    assert "grid-template-columns: minmax(180px, 1fr) 120px 140px 140px auto auto auto" in css
    assert "height: 280px" in css
    assert "resize: vertical" in css
    assert 'document.querySelector("#screen-state-confidence")' in script
    assert 'document.querySelector("#script-details")' in script
    assert 'document.querySelector("#dry-run-screen-state")' in script
    assert 'document.querySelector("#screen-state-suggestions")' in script
    assert 'document.querySelector("#use-probed-screen-state")' in script
    assert 'latestScreenState = state' in script
    assert 'dryRunScreenStateInput.value = latestScreenState' in script
    assert "没有可用探测状态" in script
    assert 'fetch("/api/screen-state-names"' in script
    assert 'fetch(`/api/script-details?name=${encodeURIComponent(scriptSelect.value)}`)' in script
    assert 'fetch("/api/start-screen-state-probe"' in script
    assert 'fetch("/api/capture-region-diagnostics"' in script


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


def test_local_ui_lists_screen_state_names_over_http() -> None:
    """验证 UI HTTP 接口可以返回界面状态候选。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/screen-state-names")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert payload == {"states": ["主页", "人物"]}


def test_local_ui_gets_script_details_over_http() -> None:
    """验证 UI HTTP 接口可以返回脚本详情。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "GET",
            "/api/script-details?name=conditional-color-demo",
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.script_detail_requests == ["conditional-color-demo"]
    assert payload == {
        "exit_code": 0,
        "name": "conditional-color-demo",
        "steps": ['If ScreenStateIs("主页")', "  then Click Point(x=100, y=200)"],
        "dependencies": ["状态: 主页"],
        "stderr": "",
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
                "dry_run_screen_state": "主页",
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
            "dry_run_screen_state": "主页",
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


def test_local_ui_starts_screen_state_probe_over_http() -> None:
    """验证 UI HTTP 接口把界面探测启动请求委托给 application。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/start-screen-state-probe",
            {
                "min_confidence": 0.75,
                "interval_seconds": 0.5,
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.probe_start_requests == [
        {
            "min_confidence": 0.75,
            "interval_seconds": 0.5,
        }
    ]
    assert payload == {
        "running": True,
        "current_state": "装备",
        "exit_code": None,
        "stdout": "probe started\n",
        "stderr": "",
    }


def test_local_ui_gets_screen_state_probe_status_over_http() -> None:
    """验证 UI HTTP 接口可以查询界面探测状态。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/screen-state-probe")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.probe_status_requests == 1
    assert payload == {
        "running": False,
        "current_state": "人物",
        "exit_code": 0,
        "stdout": "probe done\n",
        "stderr": "",
    }


def test_local_ui_stops_screen_state_probe_over_http() -> None:
    """验证 UI HTTP 接口可以请求停止界面探测。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "POST", "/api/stop-screen-state-probe", {})
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.probe_stop_requests == 1
    assert payload == {
        "running": True,
        "current_state": "装备",
        "exit_code": None,
        "stdout": "probe stopping\n",
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


def test_local_ui_captures_region_diagnostics_over_http() -> None:
    """验证 UI HTTP 接口把区域诊断请求委托给 application。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(
            server.server_address,
            "POST",
            "/api/capture-region-diagnostics",
            {},
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert app.region_diagnostics_requests == 1
    assert payload == {
        "exit_code": 0,
        "stdout": "saved region diagnostics screenshot: /tmp/latest-screen-regions.png\n",
        "stderr": "",
        "screenshot_path": "/tmp/latest-screen-regions.png",
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
        self.script_detail_requests: list[str] = []
        self.test_requests: list[str] = []
        self.image_click_requests: list[dict[str, object]] = []
        self.capture_requests = 0
        self.region_diagnostics_requests = 0
        self.probe_start_requests: list[dict[str, object]] = []
        self.probe_status_requests = 0
        self.probe_stop_requests = 0

    def list_scripts(self) -> tuple[str, ...]:
        """返回 fake 脚本列表。"""
        return ("conditional-color-demo",)

    def image_asset_folder_label(self) -> str:
        """返回 fake 图片目录展示名。"""
        return "assets"

    def list_image_assets(self) -> tuple[str, ...]:
        """返回 fake 图片资源列表。"""
        return ("start.png", "confirm.webp")

    def list_screen_state_names(self) -> tuple[str, ...]:
        """返回 fake 界面状态候选。"""
        return ("主页", "人物")

    def describe_script(self, name: str) -> ScriptDetailsResult:
        """返回 fake 脚本详情。"""
        self.script_detail_requests.append(name)
        return ScriptDetailsResult(
            exit_code=0,
            name=name,
            steps=('If ScreenStateIs("主页")', "  then Click Point(x=100, y=200)"),
            dependencies=("状态: 主页",),
        )

    def start_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str = "未知",
    ) -> ScriptRunStatus:
        """记录 fake 后台脚本启动请求。"""
        self.start_requests.append(
            {
                "name": name,
                "dry_run": dry_run,
                "dry_run_color": dry_run_color,
                "dry_run_screen_state": dry_run_screen_state,
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

    def start_screen_state_probe(
        self,
        *,
        min_confidence: float = 0.8,
        interval_seconds: float = 1.0,
    ) -> ScreenStateProbeStatus:
        """记录 fake 界面探测启动请求。"""
        self.probe_start_requests.append(
            {
                "min_confidence": min_confidence,
                "interval_seconds": interval_seconds,
            }
        )
        return ScreenStateProbeStatus(running=True, current_state="装备", stdout="probe started\n")

    def current_screen_state_probe(self) -> ScreenStateProbeStatus:
        """记录 fake 界面探测状态查询。"""
        self.probe_status_requests += 1
        return ScreenStateProbeStatus(
            running=False,
            current_state="人物",
            exit_code=0,
            stdout="probe done\n",
        )

    def stop_screen_state_probe(self) -> ScreenStateProbeStatus:
        """记录 fake 界面探测停止请求。"""
        self.probe_stop_requests += 1
        return ScreenStateProbeStatus(running=True, current_state="装备", stdout="probe stopping\n")

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

    def capture_screen_region_diagnostics(self) -> ControlResult:
        """记录 fake 区域诊断请求。"""
        self.region_diagnostics_requests += 1
        return ControlResult(
            exit_code=0,
            stdout="saved region diagnostics screenshot: /tmp/latest-screen-regions.png\n",
            stderr="",
            screenshot_path="/tmp/latest-screen-regions.png",
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
