# Star

Star 是本地桌面自动化框架，在 macOS 上执行点击、组合键、识图、条件等待和循环。用户描述任务，Agent 生成和维护脚本。主仓保存框架与通用示例，具体任务保存在仓库外的本地工作区；边界见 [ADR 0006](docs/adr/0006-local-task-workspaces.md)，能力与缺口见 [当前状态](docs/current-state.md)。

## 安装与上手

要求 Python 3.14 或更新版本。已有 `.venv` 时可直接使用。

```bash
python3.14 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/star list
.venv/bin/star run demo --dry-run
```

不指定工作区时，使用主仓的通用示例。`scripts/` 只保留文件格式示例与粘贴示例；具体游戏、聊天或其他业务任务由外部工作区保存和维护。

## 使用本地任务工作区

工作区是一个已存在的目录，常用位置为 `~/StarWorkspaces/<name>`：

```text
my-tasks/
├── scripts/                 # 命名 JSON 脚本
├── assets/                  # 模板图片，可分子目录
│   └── screen-states.json   # 按需配置的状态与共享资源
└── …                        # 任务说明、运行记录与证据
```

例如建立一个仅含粘贴示例的工作区：

```bash
mkdir -p ~/StarWorkspaces/my-tasks/scripts ~/StarWorkspaces/my-tasks/assets
cp scripts/paste.json ~/StarWorkspaces/my-tasks/scripts/
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks list
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks details 粘贴
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run 粘贴 --dry-run
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run-plan 粘贴 粘贴 --dry-run
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks ui --port 8766 --no-open
```

`--workspace` 是全局参数，放在 `list/details/run/run-plan/ui` 之前。显式指定后只加载该根的 `scripts/*.json`，并使用同根 `assets/`、状态配置和共享资源，不混入内置或主仓示例。任务资料不随框架仓库上传，需要单独备份。

浏览器打开 <http://127.0.0.1:8766/>，页面会显示当前工作区路径。一个服务绑定一个工作区；切换时启动对应服务。控制台提供脚本详情、模拟或真实运行、停止和运行记录，没有项目选择器；修改脚本后需重启服务。默认 UI 端口仍为 8765。

控制台的每次运行自动保存到所选工作区的 `.star/runs.sqlite3`。展开“历史运行”可查看最近 50 次的开始/结束时间、模式、最后步骤、结束原因和日志，并下载该次完整 JSON。日志逐条提交，重启不覆盖旧记录；若缺少结束记录，会显示“尚无结束记录”，不据此推定成功或取消。起步就无法写日志时不执行脚本，中途保存失败会在当前输出中警告。日志不主动读取剪贴板内容或截屏。

也可以从命令行查询同一工作区的控制台记录：

```bash
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks history
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks history --json
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks history RUN_ID > run-log.json
```

当前持久保存范围是控制台启动的后台运行；CLI `run` / `run-plan` 仍输出到终端。全部历史留在本机工作区，不自动删除；超过 50 次的记录仍可按 ID 导出。存储取舍见 [ADR 0007](docs/adr/0007-persistent-run-history.md)。

## 运行与停止

先模拟检查步骤，再执行真实操作：

```bash
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run 粘贴
```

粘贴示例等待 3 秒后执行 Command+V；先复制内容，再在等待期间切到目标输入框。动作发出不保证应用接受内容。真实运行需要 macOS“辅助功能”权限，识图和取色还需要“屏幕录制”权限。

模拟运行不读取或操作真实桌面。可指定固定颜色、图片集合和状态，例如在通用示例模式下：

```bash
.venv/bin/star run conditional-color-demo --dry-run --dry-run-color '#102030'
.venv/bin/star run click-image-demo --dry-run --dry-run-script-images
.venv/bin/star run file-script-demo --dry-run --dry-run-screen-state 主页
```

`--dry-run-script-images` 把当前脚本的图片依赖全部模拟为找到；这不能证明真实识图或任务完成。Run Plan 默认在首个未正常结束项后停止，`--continue-on-error` 可在普通失败或条件未满足后继续收集结果；用户取消始终终止计划，并保留取消结果。
手动使用 `--dry-run-image assets/start.png` 时，相对路径基于所选工作区根；绝对路径保持原样。

CLI 按 Ctrl+C 取消；控制台点击“停止”。取消在执行边界生效，正在进行的等待或平台调用可能延迟响应。`completed` 表示按所选分支与循环规则正常结束；`stopped_unmet_condition` 表示必要条件未满足。退出码 0 本身不证明业务任务完成。

## 目标窗口

CLI 可在真实运行前激活应用，并按标题绑定唯一的可见顶层窗口：

```bash
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run 粘贴 \
  --target-app TextEdit --target-window-title "目标文档标题"
```

绑定后，点位按窗口左上角偏移，默认图片搜索限制在窗口内。Run Plan 在每个脚本开始前重新读取窗口位置。`--target-window-title` 要求同时指定 `--target-app`；目标应用参数不能与 `--dry-run` 同用。

控制台尚未接入目标窗口选择。状态配置的区域仍是屏幕绝对坐标，不随窗口移动；模板也需要匹配当前缩放和主题。

## 创建和维护任务

用户描述目标与业务选择，Agent 在外部工作区创建脚本和素材、验证并维护。以下是 `<workspace>/scripts/my-click.json` 的最小格式参考：

```json
{
  "name": "我的点击",
  "resources": {"points": {"按钮": {"x": 100, "y": 200}}},
  "steps": [
    {"wait": 1},
    {"click": {"point": "按钮"}},
    {"hotkey": ["command", "v"]}
  ]
}
```

用相同 `--workspace` 执行 `list`、`details 我的点击` 与 `run 我的点击 --dry-run`。图片路径相对该根的 `assets/`，状态条件使用其中的 `screen-states.json`。无效脚本单独报告，不阻塞其他有效脚本。详情标明命名点位是否已配置；运行前会检查所有分支中的点位引用，未知点位以 `configuration_failed` 结束，不发出输入动作。

`repeat.times: null` 表示无限循环；`wait_until_image.timeout: null` 表示无限等待。`break_if_image` 退出当前层循环，`click.then_hotkeys` 在点击后连续发送组合键。当前没有通用重试、任务路由或子脚本调用；局部恢复仍在 [讨论稿](docs/design/local-recovery.md) 中。

运行 `.venv/bin/star recorder` 可记录屏幕坐标与颜色；终端保持焦点，按 `1` 记录、`Q` 结束。它只输出素材，不创建任务脚本。

## 开发与验证

从 [AGENTS](AGENTS.md)、[项目上下文](CONTEXT.md) 和 [文档导航](docs/README.md) 接续开发。`main` 保持稳定，框架改动使用短生命周期的通用能力分支；业务任务留在外部工作区。Windows adapter 尚未实现。

```bash
.venv/bin/python -m pytest
git diff --check
```

独立靶场只用于开发验收：

```bash
.venv/bin/star-lab --no-open
.venv/bin/python tools/visual_lab_star_smoke.py
```

靶场默认地址 <http://127.0.0.1:8770/>。真实 smoke 要求 Safari 已打开靶场且已授予桌面权限；通过独立真值核对结果，仍不能替代具体业务任务验收。
