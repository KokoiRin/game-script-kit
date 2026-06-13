## Context

当前项目已经有清晰分层：`domain` 表达脚本模型，`engine` 解释脚本步骤，`adapters` 实现平台能力，`application` 编排一次用户意图，`star_cli.py` 作为命令行入口。脚本运行已经收敛到 `application.script_run.run_script()`，但用户仍需要在终端中反复输入命令才能选择脚本、调整 dry-run 颜色并观察结果。

第一版 UI 的目标是提供一个轻量窗口入口，同时不破坏现有 port-and-adapter 结构。UI 应当和 CLI 一样是入口 adapter，而不是新的 engine port。

## Goals / Non-Goals

**Goals:**

- 提供 `star ui` 启动本地控制 UI。
- UI 可列出脚本、选择脚本、运行 dry-run 或真实模式，并展示结果。
- UI 提供固定 `Run Tests` 按钮，运行白名单测试命令并展示结果。
- UI 入口通过 application 层 use case 访问能力，保持和 CLI 同级。
- 使用轻量实现，便于端到端验证，不引入前端构建链。

**Non-Goals:**

- 不把坐标记录工具放进第一版 UI。
- 不支持用户在 UI 中输入任意 shell 命令。
- 不新增脚本编辑器、脚本文件格式或可视化流程编排。
- 不把 UI 逻辑放进 `domain`、`engine` 或平台 adapter。
- 不承诺第一版是原生桌面壳；默认打开系统浏览器窗口承载本地 UI。

## Decisions

### 1. UI 是 entrypoint adapter，不是 engine port

`star ui` 启动一个本地 HTTP UI。HTTP handler 位于入口层，只负责解析请求、调用 application use case、返回 JSON 或 HTML。它不直接创建 `ScriptRunner`，也不直接导入 `pyautogui`。

备选方案是在 `engine.ports` 里新增 UI port。这个方案会混淆概念：engine port 表示运行时设备能力，而 UI 是用户入口。第一版不采用。

### 2. 新增 application use case 收敛 UI 需要的操作

新增或复用 application 层接口：

- `list_scripts() -> tuple[str, ...]`
- `run_named_script(name, dry_run, dry_run_color) -> ApplicationResult`
- `run_tests(task_name="all") -> ApplicationResult`

这些接口隐藏脚本 catalog 查找、运行配置、测试命令白名单和错误归一化。CLI 可以继续保持现状或后续复用这些接口；UI 第一版必须通过这些接口工作。

### 3. 测试命令使用白名单

UI 的 `Run Tests` 只触发固定任务，例如 `all` 对应 `.venv/bin/python -m pytest`。后端不接受用户传入命令字符串，避免把 UI 变成通用 shell。

### 4. HTTP 服务使用 Python 标准库

使用 `http.server` 和 `json` 实现本地服务：

- `GET /` 返回 HTML 页面。
- `GET /api/scripts` 返回脚本名称。
- `POST /api/run-script` 运行脚本并返回结果。
- `POST /api/run-tests` 运行固定测试任务并返回结果。

这样可以避免 Node、React、Vite 或额外 Python Web 框架。端到端测试可通过 HTTP 直接验证接口，手动验证可打开浏览器页面。

### 5. 页面采用渐进式简单 HTML

页面内联少量 CSS/JS，提供选择框、模式切换、颜色输入、运行按钮、测试按钮和日志区域。页面文本只描述必要控件，不放大段说明。

## Risks / Trade-offs

- 标准库 HTTP server 功能有限 → 第一版仅本地单用户使用，接口保持同步阻塞，后续需要流式日志时再引入事件流。
- 真实运行脚本会阻塞请求直到完成 → 第一版接受同步完成并返回结果；长时间脚本后续再加取消和后台任务。
- `Run Tests` 可能耗时较长 → UI 按钮显示运行中状态，后端仍只运行固定白名单命令。
- 浏览器窗口不等于原生桌面壳 → 第一版先满足可用和可测；如后续确需原生窗口，可在入口层增加 pywebview/Tauri adapter，不影响 application/engine。
