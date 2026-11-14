"""验证视觉靶场 HTTP adapter、静态页面和独立启动入口。

这些测试通过真实本地 HTTP server 检查公开 contract；它不移动鼠标，
也不把靶场 API 当作 Star 的执行接口。
"""

from __future__ import annotations

import http.client
import json
import threading

from star_visual_lab import server as visual_lab_server
from star_visual_lab.scenario import TaskFlowScenario
from star_visual_lab.server import create_visual_lab_server, main


def test_visual_lab_serves_target_page_and_static_assets() -> None:
    """验证靶场页面与静态资源可由独立 server 读取。"""
    server, thread = _start_server()
    try:
        html = _request_text(server.server_address, "GET", "/")
        css = _request_text(server.server_address, "GET", "/static/lab.css")
        script = _request_text(server.server_address, "GET", "/static/lab.js")
        image = _request_bytes(
            server.server_address, "GET", "/static/images/open-tasks.png"
        )
    finally:
        _stop_server(server, thread)

    assert 'id="lab-app"' in html
    assert 'src="/static/lab.js"' in html
    assert ".lab-stage" in css
    assert 'fetch("/api/state")' in script
    assert image.startswith(b"\x89PNG\r\n\x1a\n")


def test_visual_lab_http_flow_reaches_completed_and_records_truth_events() -> None:
    """验证 HTTP 页面动作沿确定状态机完成任务并留下真值事件。"""
    scenario = TaskFlowScenario(loading_delay_seconds=0)
    server, thread = _start_server(scenario=scenario)
    try:
        initial = _request_json(server.server_address, "GET", "/api/state")
        task_list = _request_json(
            server.server_address,
            "POST",
            "/api/action",
            {"action": "open_tasks"},
        )
        loading = _request_json(
            server.server_address,
            "POST",
            "/api/action",
            {"action": "select_target"},
        )
        confirm = _request_json(server.server_address, "GET", "/api/state")
        completed = _request_json(
            server.server_address,
            "POST",
            "/api/action",
            {"action": "confirm_task"},
        )
        events = _request_json(server.server_address, "GET", "/api/events")
    finally:
        _stop_server(server, thread)

    assert initial["state"] == "home"
    assert task_list["state"] == "task_list"
    assert loading["state"] == "loading"
    assert confirm["state"] == "confirm"
    assert completed["state"] == "completed"
    assert [event["kind"] for event in events["events"]] == [
        "reset",
        "action",
        "action",
        "transition",
        "action",
    ]
    assert events["events"][-1]["to_state"] == "completed"


def test_visual_lab_http_reset_changes_fault_mode() -> None:
    """验证重置接口可确定设置目标缺失模式。"""
    server, thread = _start_server()
    try:
        reset = _request_json(
            server.server_address,
            "POST",
            "/api/reset",
            {"mode": "missing_target", "loading_delay_seconds": 2},
        )
        task_list = _request_json(
            server.server_address,
            "POST",
            "/api/action",
            {"action": "open_tasks"},
        )
    finally:
        _stop_server(server, thread)

    assert reset["mode"] == "missing_target"
    assert reset["loading_delay_seconds"] == 2
    assert task_list["state"] == "task_list"
    assert task_list["available_actions"] == []


def test_visual_lab_http_rejects_invalid_action_with_current_truth() -> None:
    """验证非法动作返回冲突状态和未改变的当前真值。"""
    server, thread = _start_server()
    try:
        status, payload = _request_json_response(
            server.server_address,
            "POST",
            "/api/action",
            {"action": "confirm_task"},
        )
    finally:
        _stop_server(server, thread)

    assert status == 409
    assert "not allowed" in payload["error"]
    assert payload["state"]["state"] == "home"


def test_visual_lab_main_maps_arguments_to_independent_server(monkeypatch) -> None:
    """验证 star-lab 入口只负责参数解析和启动服务。"""
    calls = []

    def fake_serve(**kwargs):
        """记录入口传给 server 的启动参数。"""
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(visual_lab_server, "serve_visual_lab", fake_serve)

    assert (
        main(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "9001",
                "--no-open",
                "--mode",
                "slow",
                "--loading-delay",
                "4.5",
            ]
        )
        == 0
    )
    assert calls == [
        {
            "host": "127.0.0.1",
            "port": 9001,
            "open_browser": False,
            "mode": "slow",
            "loading_delay_seconds": 4.5,
        }
    ]


def _start_server(*, scenario: TaskFlowScenario | None = None):
    """启动测试用随机端口靶场 server。"""
    server = create_visual_lab_server(host="127.0.0.1", port=0, scenario=scenario)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server, thread


def _stop_server(server, thread: threading.Thread) -> None:
    """停止并关闭测试用靶场 server。"""
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def _request_json(address, method: str, path: str, payload=None):
    """发送 HTTP 请求并返回成功 JSON。"""
    status, response = _request_json_response(address, method, path, payload)
    assert status == 200
    return response


def _request_json_response(address, method: str, path: str, payload=None):
    """发送 HTTP 请求并返回状态码和 JSON。"""
    body = None if payload is None else json.dumps(payload)
    headers = {} if body is None else {"Content-Type": "application/json"}
    connection = http.client.HTTPConnection(*address)
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    status = response.status
    result = json.loads(response.read().decode("utf-8"))
    connection.close()
    return status, result


def _request_text(address, method: str, path: str) -> str:
    """发送 HTTP 请求并返回 UTF-8 文本。"""
    return _request_bytes(address, method, path).decode("utf-8")


def _request_bytes(address, method: str, path: str) -> bytes:
    """发送 HTTP 请求并返回原始响应内容。"""
    connection = http.client.HTTPConnection(*address)
    connection.request(method, path)
    response = connection.getresponse()
    assert response.status == 200
    result = response.read()
    connection.close()
    return result
