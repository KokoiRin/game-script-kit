# Star

Star 用 JSON 脚本描述桌面操作，在 macOS 上执行点击、组合键、识图、条件等待和循环。当前重点是把一个实际任务稳定跑通。用户描述任务，Agent 负责生成和维护脚本；产品方向见 [项目上下文](CONTEXT.md)，能力与缺口见 [当前状态](docs/current-state.md)，近期推进见 [重启计划](docs/restart-plan.md)。

## 安装和启动

要求 Python 3.14 或更新版本。已有 `.venv` 时可直接使用。

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/star ui --host 127.0.0.1 --port 8766 --no-open
```

浏览器打开 <http://127.0.0.1:8766/>，选择脚本，先用“模拟运行”检查步骤，再按需执行真实操作。控制台保留脚本详情、运行、停止和运行日志。`star ui` 不指定端口时仍默认使用 8765。

真实运行需要在 macOS 系统设置中给终端或 Python 运行时授予“辅助功能”权限；识图和取色还需要“屏幕录制”权限。模板应与当前游戏缩放、主题和分辨率一致。

## 列出、检查和运行脚本

```bash
.venv/bin/star list
.venv/bin/star details 师门任务
.venv/bin/star run demo --dry-run
.venv/bin/star run 粘贴 --dry-run
.venv/bin/star run 粘贴
```

`粘贴` 脚本等待 3 秒后执行 Command+V；先复制内容，再在等待期间切到目标输入框。按键已发送不保证目标应用接受了内容。

模拟运行不操作真实桌面，可指定固定的颜色、图片和界面状态：

```bash
.venv/bin/star run conditional-color-demo --dry-run --dry-run-color '#102030'
.venv/bin/star run click-image-demo --dry-run --dry-run-image assets/start.png
.venv/bin/star run file-script-demo --dry-run --dry-run-screen-state 主页
```

`--dry-run-script-images` 可将当前脚本依赖的图片全部模拟为找到，适合检查执行顺序；这些模拟结果不证明真实识图或任务完成。

按顺序执行多个脚本：

```bash
.venv/bin/star run-plan demo repeat-demo --dry-run
```

Run Plan 默认在第一个未正常结束的脚本后停止；`--continue-on-error` 可继续收集后续结果。检查 `finish_reason`：`completed` 表示脚本按所选分支与循环规则正常结束，`stopped_unmet_condition` 表示条件未满足。退出码 0 本身不能证明游戏任务完成。

CLI 运行时按 Ctrl+C 取消；控制台运行时点击“停止”。无限循环和无限图片等待也支持取消。

## 绑定目标应用和窗口

真实运行可先激活应用，并限制到标题唯一匹配的可见顶层窗口：

```bash
.venv/bin/star run click-image-demo \
  --target-app Safari \
  --target-window-title "Star 视觉自动化靶场"
.venv/bin/star run-plan first-script second-script --target-app Safari
```

指定窗口后，点位按该窗口左上角偏移，未声明 region 的图片搜索限制在窗口内；Run Plan 在每个脚本开始前重新读取窗口位置。浏览器标签页不是独立窗口，必要时把目标页面移到单独窗口。

`--target-window-title` 要求同时提供 `--target-app`；目标应用参数不能与 `--dry-run` 同用。控制台目前尚未接入目标应用和窗口选择，需使用 CLI 指定。

界面状态配置中的区域目前仍使用屏幕绝对坐标，不会随目标窗口移动；使用状态判断的脚本仍需保持约定的窗口位置。

## 编写脚本

通常由用户描述任务、Agent 创建和维护下面的文件；用户无需手写 JSON。这里保留格式参考，便于检查或自行调整。

用户脚本放在 `scripts/*.json`，模板图片放在 `assets/`。例如新建 `scripts/my-click.json`：

```json
{
  "name": "我的点击",
  "resources": {
    "points": {"按钮": {"x": 100, "y": 200}}
  },
  "steps": [
    {"wait": 1},
    {"click": {"point": "按钮"}},
    {"hotkey": ["command", "v"]}
  ]
}
```

用 `list` 确认名称可见，`details 我的点击` 检查依赖，再 `run 我的点击 --dry-run` 检查顺序。默认点位是屏幕坐标；绑定目标窗口后使用窗口内坐标。无效脚本单独报告，不阻塞其他有效脚本。

可参考 [师门任务](scripts/master-task.json) 的区域识图和状态等待，以及 [匿名聊天循环](scripts/ssby-chat-loop.json) 的嵌套循环。这些脚本是现有素材，真实任务闭环状态见重启计划。

- `repeat` 的 `times: null` 表示无限循环；`wait_until_image` 的 `timeout: null` 表示无限等待，省略字段不等于无限。
- `break_if_image` 在步骤边界和图片等待轮询时检查，命中后退出当前层循环。
- `click.then_hotkeys` 在点击后连续发送组合键；取消仍在每组按键前检查。
- `if_state` 和 `wait_until_state` 使用 `assets/screen-states.json` 中的界面识别配置。

记录鼠标所在位置和颜色：

```bash
.venv/bin/star recorder
```

保持终端焦点，按 `1` 记录，按 `Q` 结束；记录结果是屏幕绝对坐标。

## 开发和验证

核心规则位于 `src/game_automation/portable/`；桌面适配和 CLI/UI 入口位于 `src/game_automation/platform/`。开发前阅读 [AGENTS.md](AGENTS.md)，按 [文档入口](docs/README.md) 接续上下文、架构和相关决策。Windows adapter 尚未实现。

```bash
.venv/bin/python -m pytest
git diff --check
```

`star-lab` 仅用于开发验收，是独立目标应用，可验证真实截图、识图、点击和等待：

```bash
.venv/bin/star-lab --no-open
.venv/bin/python tools/visual_lab_star_smoke.py
```

靶场默认地址 <http://127.0.0.1:8770/>。真实 smoke 要求 Safari 已打开靶场页面，并已授予屏幕录制和辅助功能权限；验收通过靶场真值接口确认结果。靶场通过不等于真实游戏任务已完成。
