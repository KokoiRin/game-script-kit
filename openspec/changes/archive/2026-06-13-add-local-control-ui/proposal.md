## Why

当前只能通过 CLI 选择和运行脚本，反复 dry-run、调整颜色条件和查看结果不够直观。新增一个轻量本地控制 UI，可以让用户用窗口入口控制脚本运行，同时给后续端到端测试提供稳定入口。

## What Changes

- 新增 `star ui` 子命令，启动本地控制 UI 服务，并默认打开本机浏览器窗口。
- UI 展示内置脚本列表，支持选择脚本并以 dry-run 或真实模式运行。
- UI 支持输入 dry-run 固定颜色，并展示脚本运行退出码、输出日志和错误信息。
- UI 提供固定 `Run Tests` 按钮，只运行项目白名单测试命令，不接受用户输入任意 shell 命令。
- UI 作为入口 adapter 调用 application 层用例，不直接解释脚本步骤，也不直接创建平台自动化 adapter。
- 不把坐标记录工具放进第一版 UI；`star recorder` 继续在终端中使用。
- 不引入前端构建链；第一版使用轻量本地 HTML/HTTP 接口。

## Capabilities

### New Capabilities

- `local-control-ui`: 本地控制 UI 的启动、脚本运行、固定测试运行和端到端验证入口。

### Modified Capabilities

- 无。

## Impact

- 受影响代码：`src/game_automation/application/`、新增 UI entrypoint module、`src/game_automation/star_cli.py`、`pyproject.toml` 如需依赖声明、`README.md`。
- 测试影响：新增 application/UI 接口测试、CLI `star ui` 测试、HTTP 端到端风格测试；保留现有 CLI/runner/domain 测试。
- 依赖影响：优先使用 Python 标准库实现本地服务和页面；除非窗口壳非常轻量且必要，否则不新增运行时依赖。
