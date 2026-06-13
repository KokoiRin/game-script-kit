"""本地控制 UI 的 HTTP 入口 adapter。

本 module 负责把浏览器页面和 JSON 请求转换为 application 调用；它不直接运行
脚本、不导入平台自动化 adapter，也不提供通用命令执行能力。
"""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from game_automation.platform.local_desktop.composition import build_local_control_application
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

    class LocalControlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_html(CONTROL_PAGE_HTML)
                return
            if self.path == "/api/scripts":
                self._send_json({"scripts": list(control_app.list_scripts())})
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path == "/api/run-script":
                payload = self._read_json()
                result = control_app.run_named_script(
                    str(payload.get("name", "")),
                    dry_run=bool(payload.get("dry_run", True)),
                    dry_run_color=str(payload.get("dry_run_color", "#000000")),
                )
                self._send_json(_result_to_payload(result))
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

        def _send_html(self, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return ThreadingHTTPServer((host, port), LocalControlHandler)


def _result_to_payload(result) -> dict[str, object]:
    """把 application 结果转换成 HTTP JSON payload。"""
    return {
        "exit_code": result.exit_code,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


CONTROL_PAGE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Star 控制台</title>
  <style>
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #15171a;
    }
    body {
      margin: 0;
      min-height: 100vh;
    }
    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 20px 36px;
    }
    header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: center;
      margin-bottom: 20px;
    }
    h1 {
      font-size: 28px;
      line-height: 1.2;
      margin: 0;
      font-weight: 700;
    }
    .toolbar {
      display: grid;
      grid-template-columns: minmax(180px, 1fr) 120px 140px auto;
      gap: 10px;
      align-items: end;
      background: #ffffff;
      border: 1px solid #d8dde5;
      border-radius: 8px;
      padding: 14px;
    }
    label {
      display: grid;
      gap: 6px;
      font-size: 13px;
      color: #4e5661;
    }
    select, input {
      height: 36px;
      border: 1px solid #bfc7d2;
      border-radius: 6px;
      padding: 0 10px;
      font: inherit;
      background: #ffffff;
      color: #15171a;
    }
    input[type="checkbox"] {
      width: 18px;
      height: 18px;
      margin: 0;
      accent-color: #2563eb;
    }
    .checkbox-label {
      min-height: 36px;
      display: flex;
      flex-direction: row;
      align-items: center;
      gap: 8px;
      color: #15171a;
      font-size: 14px;
    }
    button {
      height: 36px;
      border: 1px solid #1d4ed8;
      border-radius: 6px;
      padding: 0 12px;
      font: inherit;
      font-weight: 600;
      background: #2563eb;
      color: #ffffff;
      cursor: pointer;
    }
    button.secondary {
      border-color: #6b7280;
      background: #ffffff;
      color: #1f2937;
    }
    button:disabled {
      opacity: 0.62;
      cursor: not-allowed;
    }
    .output {
      margin-top: 16px;
      display: grid;
      gap: 10px;
    }
    .status {
      min-height: 24px;
      font-weight: 600;
    }
    pre {
      min-height: 280px;
      margin: 0;
      padding: 14px;
      border-radius: 8px;
      border: 1px solid #2f3542;
      background: #111827;
      color: #e5e7eb;
      overflow: auto;
      white-space: pre-wrap;
      font-size: 13px;
      line-height: 1.45;
    }
    @media (max-width: 760px) {
      header, .toolbar {
        display: grid;
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Star 控制台</h1>
      <button class="secondary" id="run-tests" type="button">运行测试</button>
    </header>
    <section class="toolbar">
      <label>
        脚本
        <select id="script-select"></select>
      </label>
      <label class="checkbox-label">
        <input id="dry-run-enabled" type="checkbox" checked>
        模拟运行
      </label>
      <label>
        模拟颜色
        <input id="dry-run-color" value="#000000" pattern="#[0-9A-Fa-f]{6}">
      </label>
      <button id="run-script" type="button">运行脚本</button>
    </section>
    <section class="output">
      <div class="status" id="status"></div>
      <pre id="output"></pre>
    </section>
  </main>
  <script>
    const scriptSelect = document.querySelector("#script-select");
    const dryRunCheckbox = document.querySelector("#dry-run-enabled");
    const colorInput = document.querySelector("#dry-run-color");
    const statusEl = document.querySelector("#status");
    const outputEl = document.querySelector("#output");
    const runScriptButton = document.querySelector("#run-script");
    const runTestsButton = document.querySelector("#run-tests");

    function setBusy(isBusy) {
      runScriptButton.disabled = isBusy;
      runTestsButton.disabled = isBusy;
    }

    function renderResult(prefix, result) {
      statusEl.textContent = `${prefix}退出码：${result.exit_code}`;
      outputEl.textContent = `${result.stdout || ""}${result.stderr || ""}`;
    }

    async function loadScripts() {
      const response = await fetch("/api/scripts");
      const payload = await response.json();
      scriptSelect.innerHTML = "";
      for (const name of payload.scripts) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        scriptSelect.appendChild(option);
      }
    }

    async function runScript() {
      setBusy(true);
      statusEl.textContent = "正在运行脚本...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/run-script", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            name: scriptSelect.value,
            dry_run: dryRunCheckbox.checked,
            dry_run_color: colorInput.value
          })
        });
        renderResult("脚本", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function runTests() {
      setBusy(true);
      statusEl.textContent = "正在运行测试...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/run-tests", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({task: "all"})
        });
        renderResult("测试", await response.json());
      } finally {
        setBusy(false);
      }
    }

    runScriptButton.addEventListener("click", runScript);
    runTestsButton.addEventListener("click", runTests);
    loadScripts();
  </script>
</body>
</html>
"""
