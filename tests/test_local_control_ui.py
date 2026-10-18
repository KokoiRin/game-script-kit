"""通过真实本地 HTTP 请求验证控制台入口契约。

本 module 覆盖脚本列表、详情、模拟运行、状态与停止，以及已移除调试接口的
不可达行为；平台输入由应用 fake 或真实 dry-run 隔离，不操作桌面设备。
"""

from __future__ import annotations

import http.client
import json
import threading

import pytest

from game_automation.portable.application.local_control import (
    LocalControlApplication,
    ScriptRunStatus,
)
from game_automation.portable.application.script_details import ScriptDetailsResult
from game_automation.portable.application.config_script_loader import ScriptConfigError
from game_automation.portable.application.project_assets import SCRIPT_FOLDER
from game_automation.portable.application.project_scripts import (
    load_project_script_catalog,
    load_project_script_catalog_result,
)
from game_automation.portable.scripts_manager.catalog import ScriptCatalog
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


@pytest.mark.parametrize("step,summary,output", [
    ({"wait": 0}, "Wait 0s", "wait 0.0s"),
    ({"hotkey": ["command", "v"]}, "Hotkey command+v", "hotkey command+v"),
])
def test_local_ui_uses_file_backed_scripts_over_http(tmp_path, step, summary, output) -> None:
    """UI 应能列出文件脚本、展示等待或组合键详情，并通过模拟运行返回对应动作。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "user.json").write_text(
        json.dumps({"name": "用户脚本", "steps": [step]}),
        encoding="utf-8",
    )
    catalog = load_project_script_catalog(tmp_path, base_catalog=ScriptCatalog(()))
    app = LocalControlApplication(catalog=catalog, project_root=tmp_path)
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        scripts_payload = _request_json(server.server_address, "GET", "/api/scripts")
        details_payload = _request_json(
            server.server_address,
            "GET",
            "/api/script-details?name=%E7%94%A8%E6%88%B7%E8%84%9A%E6%9C%AC",
        )
        run_payload = _request_json(
            server.server_address,
            "POST",
            "/api/run-script",
            {
                "name": "用户脚本",
                "dry_run": True,
                "dry_run_color": "#000000",
                "dry_run_screen_state": "未知",
                "dry_run_images": [],
            },
        )
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert scripts_payload["scripts"] == ["用户脚本"]
    assert details_payload["name"] == "用户脚本"
    assert details_payload["steps"] == [summary]
    assert run_payload["exit_code"] == 0
    assert output in run_payload["stdout"]


def test_local_ui_reports_bad_file_scripts_over_http(tmp_path) -> None:
    """验证 UI 脚本列表接口返回可用脚本和坏脚本配置错误。"""
    script_dir = tmp_path / SCRIPT_FOLDER
    script_dir.mkdir()
    (script_dir / "good.json").write_text(
        '{"name": "good", "steps": [{"wait": 0}]}',
        encoding="utf-8",
    )
    (script_dir / "bad.json").write_text(
        '{"name": "bad", "steps": [{"drag": {}}]}',
        encoding="utf-8",
    )
    catalog_result = load_project_script_catalog_result(tmp_path, base_catalog=ScriptCatalog(()))
    app = LocalControlApplication(
        catalog=catalog_result.catalog,
        script_config_errors=catalog_result.script_config_errors,
        project_root=tmp_path,
    )
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        payload = _request_json(server.server_address, "GET", "/api/scripts")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert payload["scripts"] == ["good"]
    assert payload["script_config_errors"] == [
        {
            "file": "bad.json",
            "message": "bad.json: unsupported step type: drag",
        }
    ]


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
        "steps": [
            'If ScreenStateIs("主页")',
            "  then Click Point(x=100, y=200)",
            'WaitUntil ScreenStateIs("主页") timeout=1s interval=0.5s',
        ],
        "dependencies": ["状态: 主页"],
        "state_dependencies": ["主页"],
        "point_dependencies": ["头像"],
        "state_waits": ["主页"],
        "state_decisions": [
            {
                "state": "主页",
                "matched_steps": ["Click Point(x=100, y=200)"],
                "unmatched_steps": ["Wait 0.5s"],
            }
        ],
        "image_dependencies": ["assets/start.png"],
        "readiness": [
            {"label": "状态: 主页", "status": "ok", "message": "状态已配置"},
        ],
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
                "dry_run_images": ["assets/start.png"],
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
            "dry_run_images": ("assets/start.png",),
        }
    ]
    assert payload == {
        "running": True,
        "exit_code": None,
        "finish_reason": "running",
        "stdout": "started\n",
        "stderr": "",
        "events": [],
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
        "finish_reason": "completed",
        "stdout": "done\n",
        "stderr": "",
        "events": [],
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
        "finish_reason": "running",
        "stdout": "stopping\n",
        "stderr": "",
        "events": [],
    }


def _request_json(address, method: str, path: str, body: dict[str, object] | None = None) -> dict[str, object]:
    """请求公开 HTTP 接口并解析成功的 JSON 响应。"""
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
    """请求页面或静态资源并返回成功的文本响应。"""
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        data = response.read().decode("utf-8")
    finally:
        connection.close()
    assert response.status == 200
    return data


class FakeControlApplication:
    """仅实现控制台保留的应用接口，避免调试接口被意外恢复。"""

    def __init__(self) -> None:
        """初始化脚本运行请求记录。"""
        self.start_requests: list[dict[str, object]] = []
        self.status_requests = 0
        self.stop_requests = 0
        self.script_detail_requests: list[str] = []

    def list_scripts(self) -> tuple[str, ...]:
        """返回 fake 脚本列表。"""
        return ("conditional-color-demo",)

    def list_script_config_errors(self) -> tuple[ScriptConfigError, ...]:
        """返回 fake 脚本配置错误。"""
        return ()

    def list_screen_state_names(self) -> tuple[str, ...]:
        """返回 fake 界面状态候选。"""
        return ("主页", "人物")

    def describe_script(self, name: str) -> ScriptDetailsResult:
        """返回 fake 脚本详情。"""
        self.script_detail_requests.append(name)
        return ScriptDetailsResult(
            exit_code=0,
            name=name,
            steps=(
                'If ScreenStateIs("主页")',
                "  then Click Point(x=100, y=200)",
                'WaitUntil ScreenStateIs("主页") timeout=1s interval=0.5s',
            ),
            dependencies=("状态: 主页",),
            state_dependencies=("主页",),
            point_dependencies=("头像",),
            state_waits=("主页",),
            state_decisions=(
                ("主页", ("Click Point(x=100, y=200)",), ("Wait 0.5s",)),
            ),
            image_dependencies=("assets/start.png",),
            readiness=(("状态: 主页", "ok", "状态已配置"),),
        )

    def start_named_script(
        self,
        name: str,
        *,
        dry_run: bool,
        dry_run_color: str,
        dry_run_screen_state: str = "未知",
        dry_run_images: tuple[str, ...] = (),
    ) -> ScriptRunStatus:
        """记录 fake 后台脚本启动请求。"""
        self.start_requests.append(
            {
                "name": name,
                "dry_run": dry_run,
                "dry_run_color": dry_run_color,
                "dry_run_screen_state": dry_run_screen_state,
                "dry_run_images": dry_run_images,
            }
        )
        return ScriptRunStatus(running=True, stdout="started\n")

    def current_script_run(self) -> ScriptRunStatus:
        """记录 fake 后台脚本状态查询。"""
        self.status_requests += 1
        return ScriptRunStatus(running=False, exit_code=0, stdout="done\n", finish_reason="completed")

    def stop_running_script(self) -> ScriptRunStatus:
        """记录 fake 后台脚本停止请求。"""
        self.stop_requests += 1
        return ScriptRunStatus(running=True, stdout="stopping\n")


@pytest.fixture
def control_server():
    """启动只实现保留接口的 HTTP server，并在用例后关闭。"""
    app = FakeControlApplication()
    server = create_local_control_server(host="127.0.0.1", port=0, app=app)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    try:
        yield server.server_address, app
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_local_ui_serves_focused_control_page(control_server) -> None:
    """页面保留默认模拟、运行、停止和结果，同时移除所有调试工作台入口。"""
    address, _ = control_server
    html = _request_text(address, "GET", "/")
    for element_id in ("script-select", "run-script", "stop-script", "script-details", "output", "status", "run-mode"):
        assert f'id="{element_id}"' in html
    assert 'id="dry-run-enabled" type="checkbox" checked' in html
    for label in ("运行测试", "查找并点击图片", "截屏诊断", "环境诊断", "区域诊断", "区域裁剪", "界面探测", "区域匹配预览"):
        assert label not in html


@pytest.mark.parametrize("path", ["/static/control.css", "/static/control.js"])
def test_local_ui_serves_static_assets(control_server, path) -> None:
    """控制台通过公开静态路径提供非空样式和交互资源。"""
    address, _ = control_server
    assert len(_request_text(address, "GET", path)) > 100


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/image-assets"),
    ("GET", "/api/screen-state-config"),
    ("GET", "/api/screen-state-probe"),
    ("GET", "/api/debug-screenshot"),
    ("POST", "/api/run-tests"),
    ("POST", "/api/click-image"),
    ("POST", "/api/preview-image-match"),
    ("POST", "/api/capture-screen"),
    ("POST", "/api/diagnose-screen"),
    ("POST", "/api/capture-region-diagnostics"),
    ("POST", "/api/capture-probe-diagnostics"),
    ("POST", "/api/capture-region-crops"),
    ("POST", "/api/capture-probe-crops"),
    ("POST", "/api/start-screen-state-probe"),
    ("POST", "/api/stop-screen-state-probe"),
    ("GET", "/static/../local_ui.py"),
])
def test_local_ui_removed_debug_endpoints_are_not_found(control_server, method, path) -> None:
    """删除后的调试接口和非白名单静态路径返回 404，不委托应用层。"""
    address, app = control_server
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    try:
        connection.request(method, path)
        response = connection.getresponse()
        response.read()
    finally:
        connection.close()
    assert response.status == 404
    assert app.start_requests == []
    assert app.stop_requests == 0


@pytest.mark.parametrize("body", ["not-json", "[]", '"text"'])
def test_local_ui_invalid_run_request_does_not_start_script(control_server, body) -> None:
    """非法 JSON 或非对象运行请求返回 400，不能触发脚本。"""
    address, app = control_server
    connection = http.client.HTTPConnection(address[0], address[1], timeout=5)
    try:
        connection.request("POST", "/api/run-script", body=body, headers={"Content-Type": "application/json"})
        response = connection.getresponse()
        response.read()
    finally:
        connection.close()
    assert response.status == 400
    assert app.start_requests == []


@pytest.mark.parametrize("finish_reason,exit_code", [
    ("completed", 0),
    ("stopped_unmet_condition", 0),
    ("cancelled", 0),
    ("setup_failed", 1),
    ("configuration_failed", 2),
])
def test_local_ui_preserves_finish_reason_in_status(control_server, monkeypatch, finish_reason, exit_code) -> None:
    """HTTP 状态保留实际完成原因，不能把退出码为零的提前停止当作完成。"""
    address, app = control_server
    monkeypatch.setattr(app, "current_script_run", lambda: ScriptRunStatus(
        running=False, exit_code=exit_code, finish_reason=finish_reason,
    ))
    payload = _request_json(address, "GET", "/api/script-run")
    assert payload["finish_reason"] == finish_reason
    assert payload["exit_code"] == exit_code
