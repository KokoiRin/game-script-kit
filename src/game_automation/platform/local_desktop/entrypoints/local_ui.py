"""本地控制 UI 的 HTTP 入口 adapter。

本 module 负责把浏览器页面和 JSON 请求转换为 application 调用；它不直接运行
脚本、不导入平台自动化 adapter，也不提供通用命令执行能力。
"""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
    latest_screenshot_path = ""
    screenshot_version = 0

    class LocalControlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """处理控制页面、脚本列表和图片资源列表读取请求。"""
            path = self.path.split("?", 1)[0]
            if path == "/":
                self._send_html(CONTROL_PAGE_HTML)
                return
            if path == "/api/scripts":
                self._send_json({"scripts": list(control_app.list_scripts())})
                return
            if path == "/api/image-assets":
                self._send_json(
                    {
                        "asset_folder": control_app.image_asset_folder_label(),
                        "assets": list(control_app.list_image_assets()),
                    }
                )
                return
            if path == "/api/script-run":
                self._send_json(_status_to_payload(control_app.current_script_run()))
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
                )
                self._send_json(_status_to_payload(status))
                return
            if self.path == "/api/stop-script":
                status = control_app.stop_running_script()
                self._send_json(_status_to_payload(status))
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


def _parse_min_confidence(payload: dict[str, object]) -> float | None:
    """把 HTTP payload 中的图片匹配置信度解析为数字。"""
    try:
        return float(payload.get("min_confidence", 0.8))
    except (TypeError, ValueError):
        return None


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
      grid-template-columns: minmax(180px, 1fr) 120px 140px auto auto;
      gap: 10px;
      align-items: end;
      background: #ffffff;
      border: 1px solid #d8dde5;
      border-radius: 8px;
      padding: 14px;
    }
    .image-toolbar {
      margin-top: 12px;
      display: grid;
      grid-template-columns: minmax(180px, 1fr) 120px auto auto auto;
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
    .debug-preview {
      display: none;
      margin-top: 12px;
      border: 1px solid #bfc7d2;
      border-radius: 8px;
      background: #ffffff;
      overflow: auto;
      max-height: 460px;
    }
    .debug-preview img {
      display: block;
      max-width: 100%;
      height: auto;
    }
    @media (max-width: 760px) {
      header, .toolbar, .image-toolbar {
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
      <button class="secondary" id="stop-script" type="button" disabled>停止</button>
    </section>
    <section class="image-toolbar">
      <label>
        目标图片 <span id="image-asset-folder">assets</span>/
        <select id="image-asset-select"></select>
      </label>
      <label>
        最低置信度
        <input id="image-confidence" type="number" min="0.01" max="1" step="0.01" value="0.8">
      </label>
      <button class="secondary" id="refresh-images" type="button">刷新图片</button>
      <button class="secondary" id="capture-screen" type="button">截屏诊断</button>
      <button id="click-image" type="button">查找并点击图片</button>
    </section>
    <section class="output">
      <div class="status" id="status"></div>
      <pre id="output"></pre>
      <div class="debug-preview" id="debug-preview">
        <img id="debug-screenshot" alt="最新截屏诊断图">
      </div>
    </section>
  </main>
  <script>
    const scriptSelect = document.querySelector("#script-select");
    const dryRunCheckbox = document.querySelector("#dry-run-enabled");
    const colorInput = document.querySelector("#dry-run-color");
    const statusEl = document.querySelector("#status");
    const outputEl = document.querySelector("#output");
    const runScriptButton = document.querySelector("#run-script");
    const stopScriptButton = document.querySelector("#stop-script");
    const runTestsButton = document.querySelector("#run-tests");
    const imageAssetSelect = document.querySelector("#image-asset-select");
    const imageAssetFolder = document.querySelector("#image-asset-folder");
    const refreshImagesButton = document.querySelector("#refresh-images");
    const clickImageButton = document.querySelector("#click-image");
    const captureScreenButton = document.querySelector("#capture-screen");
    const imageConfidenceInput = document.querySelector("#image-confidence");
    const debugPreview = document.querySelector("#debug-preview");
    const debugScreenshot = document.querySelector("#debug-screenshot");
    let scriptRunPollTimer = null;
    let activeScriptRun = false;

    function setBusy(isBusy) {
      runScriptButton.disabled = isBusy;
      runTestsButton.disabled = isBusy;
      refreshImagesButton.disabled = isBusy;
      captureScreenButton.disabled = isBusy;
      clickImageButton.disabled = isBusy || !imageAssetSelect.value;
      stopScriptButton.disabled = !activeScriptRun;
    }

    function renderResult(prefix, result) {
      statusEl.textContent = `${prefix}退出码：${result.exit_code}`;
      outputEl.textContent = `${result.stdout || ""}${result.stderr || ""}`;
      if (result.screenshot_url) {
        debugScreenshot.src = result.screenshot_url;
        debugPreview.style.display = "block";
      }
    }

    function renderScriptStatus(result) {
      if (result.running) {
        statusEl.textContent = "脚本运行中...";
      } else if (result.exit_code === null || result.exit_code === undefined) {
        statusEl.textContent = "脚本未运行";
      } else {
        statusEl.textContent = `脚本退出码：${result.exit_code}`;
      }
      outputEl.textContent = `${result.stdout || ""}${result.stderr || ""}`;
    }

    function scheduleScriptRunPoll() {
      if (scriptRunPollTimer) {
        window.clearTimeout(scriptRunPollTimer);
      }
      scriptRunPollTimer = window.setTimeout(pollScriptRun, 500);
    }

    async function pollScriptRun() {
      const response = await fetch("/api/script-run");
      const result = await response.json();
      renderScriptStatus(result);
      activeScriptRun = Boolean(result.running);
      setBusy(activeScriptRun);
      if (activeScriptRun) {
        scheduleScriptRunPoll();
      }
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

    async function loadImageAssets() {
      const response = await fetch("/api/image-assets");
      const payload = await response.json();
      imageAssetFolder.textContent = payload.asset_folder || "assets";
      imageAssetSelect.innerHTML = "";
      for (const name of payload.assets || []) {
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        imageAssetSelect.appendChild(option);
      }
      setBusy(false);
    }

    async function runScript() {
      activeScriptRun = true;
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
        const result = await response.json();
        renderScriptStatus(result);
        activeScriptRun = Boolean(result.running);
        setBusy(activeScriptRun);
        if (activeScriptRun) {
          scheduleScriptRunPoll();
        }
      } finally {
        setBusy(activeScriptRun);
      }
    }

    async function stopScript() {
      statusEl.textContent = "正在停止脚本...";
      try {
        const response = await fetch("/api/stop-script", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        const result = await response.json();
        renderScriptStatus(result);
        activeScriptRun = Boolean(result.running);
        setBusy(activeScriptRun);
        if (activeScriptRun) {
          scheduleScriptRunPoll();
        }
      } finally {
        stopScriptButton.disabled = !activeScriptRun;
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

    async function clickImage() {
      setBusy(true);
      statusEl.textContent = "正在查找图片...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/click-image", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({
            asset: imageAssetSelect.value,
            dry_run: dryRunCheckbox.checked,
            min_confidence: Number.parseFloat(imageConfidenceInput.value)
          })
        });
        renderResult("图片点击", await response.json());
      } finally {
        setBusy(false);
      }
    }

    async function captureScreen() {
      setBusy(true);
      statusEl.textContent = "正在截屏...";
      outputEl.textContent = "";
      try {
        const response = await fetch("/api/capture-screen", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({})
        });
        renderResult("截屏诊断", await response.json());
      } finally {
        setBusy(false);
      }
    }

    runScriptButton.addEventListener("click", runScript);
    stopScriptButton.addEventListener("click", stopScript);
    runTestsButton.addEventListener("click", runTests);
    refreshImagesButton.addEventListener("click", loadImageAssets);
    captureScreenButton.addEventListener("click", captureScreen);
    clickImageButton.addEventListener("click", clickImage);
    loadScripts();
    loadImageAssets();
  </script>
</body>
</html>
"""
