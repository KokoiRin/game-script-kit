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

## macOS 原生应用

桌面界面使用 SwiftUI + AppKit，支持素材准备与脚本运行；不需要 Qt、浏览器或本地 Web 服务。要求 macOS 13+、Swift 5.9+（Xcode 或 Command Line Tools）。首次构建：

```bash
swift build --package-path native/StarDesktop
.venv/bin/star ui
```

未指定工作区时使用原生目录选择器。也可生成从 Finder 打开的开发应用：

```bash
.venv/bin/python tools/build_macos_app.py
open native/StarDesktop/dist/Star.app
```

建议安装到当前用户的“应用程序”，方便从 Finder 打开并确认授权对象：

```bash
.venv/bin/python tools/build_macos_app.py --install
open ~/Applications/Star.app
```

首次进入后，顶部“系统权限”分别显示窗口控制与屏幕截图状态；点击所需权限的申请按钮，按系统提示确认。返回后会重新检测，必要时可点击“重启后台”。查询状态不主动申请权限，模拟运行不要求授权。构建器不申请权限；当前应用使用本地临时签名，仍绑定本机仓库与 Python 环境，尚未打包 Python 或进行发布签名、公证。SwiftPM 与本机工具链不兼容时，可显式加上 `--compiler swiftc`，按相同的 macOS 13 最低版本直接编译。详情见 [原生壳说明](native/StarDesktop/README.md) 和 [ADR 0008](docs/adr/0008-native-macos-desktop.md)。

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
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks ui
```

`--workspace` 是全局参数，放在 `list/details/run/run-plan/ui` 之前。显式指定后只加载该根的 `scripts/*.json`，并使用同根 `assets/`、状态配置和共享资源，不混入内置或主仓示例。任务资料不随框架仓库上传，需要单独备份。

原生应用显示当前工作区。切换目录时先回收旧后台，再启动绑定新目录的后台；同一工作区只允许一个后台。运行页提供脚本详情、模拟或真实运行、停止和运行记录；修改脚本后点击“重新加载”。旧 `--host/--port/--no-open` 网页参数已移除。

## 运行与停止

先模拟检查步骤，再执行真实操作：

```bash
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run 粘贴
```

粘贴示例等待 3 秒后执行 Command+V；先复制内容，再在等待期间切到目标输入框。动作发出不保证应用接受内容。真实运行需要 macOS“辅助功能”权限，识图和取色还需要“屏幕录制”权限。

运行前会校验全部分支中的点位、图片、搜索和区域引用；未定义引用返回 `configuration_failed`，不会先执行前序动作。`details` 检出缺失依赖时返回退出码 2，仍展示步骤与检查明细。模拟运行不要求模板文件实际存在，但资源别名必须已定义。

模拟运行不读取或操作真实桌面。可指定固定颜色、图片集合和状态，例如在通用示例模式下：

```bash
.venv/bin/star run conditional-color-demo --dry-run --dry-run-color '#102030'
.venv/bin/star run click-image-demo --dry-run --dry-run-script-images
.venv/bin/star run file-script-demo --dry-run --dry-run-screen-state 主页
```

`--dry-run-script-images` 把当前脚本的图片依赖全部模拟为找到；这不能证明真实识图或任务完成。Run Plan 默认在首个未正常结束项后停止，`--continue-on-error` 可继续收集普通失败后的结果；用户取消始终结束整轮，返回 `130/cancelled`，各项结果保留。
手动使用 `--dry-run-image assets/start.png` 时，相对路径基于所选工作区根；绝对路径保持原样。

CLI 按 Ctrl+C 取消；原生运行页点击“停止脚本”。后台真实等待每最多 50ms 检查取消，正在进行的平台调用仍可能延迟响应。关闭原生应用会先请求停止再回收后台，详情与异常回收记录保存在工作区 `.star/desktop.log`。`completed` 表示按所选分支与循环规则正常结束；`stopped_unmet_condition` 表示必要条件未满足。退出码 0 本身不证明业务任务完成。

## 目标窗口

CLI 可在真实运行前激活应用，并按标题绑定唯一的可见顶层窗口：

```bash
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks run 粘贴 \
  --target-app TextEdit --target-window-title "目标文档标题"
```

绑定后，点位按窗口左上角偏移，默认图片搜索限制在窗口内。Run Plan 在每个脚本开始前重新读取窗口位置。`--target-window-title` 要求同时指定 `--target-app`；目标应用参数不能与 `--dry-run` 同用。

控制台尚未接入目标窗口选择。状态配置的区域仍是屏幕绝对坐标，不随窗口移动；模板也需要匹配当前缩放和主题。

## 实时识别窗口状态

在素材准备页登记状态素材及搜索范围，再进入“实时识别”页选择窗口，点击“开始观察”。支持每秒 1、2 或 5 次采样、连续帧确认、每条素材的证据及状态变化记录。停止、截图失败和过期结果不输出有效状态。

窗口规则与素材保存在所选任务工作区。首次使用流程、坐标约定和限制见 [原生应用说明](native/StarDesktop/README.md#登记素材并开始实时识别)。观察保持只读，暂不驱动脚本动作。

## 创建和维护任务

在原生应用的素材准备页采集点位和模板：

```bash
mkdir -p ~/StarWorkspaces/my-tasks
.venv/bin/star --workspace ~/StarWorkspaces/my-tasks prepare
```

填写目标应用名，读取并选择窗口，然后截取画面。截图会切换目标应用，完成后原生壳回到前台；点击冻结画面获取窗口相对点位，拖动框选后填写名称保存模板。
模板写入该工作区的 `assets/<名称>.png`，界面给出可复制的资源片段供 Agent 生成脚本；当前不自动写入脚本或状态配置，重名模板不会覆盖。

准备与执行用例仍独立，在同一个原生壳组合；只有进入运行功能才加载脚本目录，运行时禁止并发操作素材。`prepare` 要求显式工作区。窗口相对点位运行时仍须通过 CLI 显式传递 `--target-app/--target-window-title`，准备选窗不会自动绑定运行目标。

当前是手动冻结截图，支持主屏幕范围内的 macOS 窗口；系统需授予辅助功能与屏幕录制权限。新截图会使旧帧框选失效，多显示器、持续画面和状态驱动仍待扩展；设计见 [ADR 0007](docs/adr/0007-preparation-and-execution.md)。

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

用相同 `--workspace` 执行 `list`、`details 我的点击` 与 `run 我的点击 --dry-run`。图片路径相对该根的 `assets/`，状态条件使用其中的 `screen-states.json`。无效脚本单独报告，不阻塞其他有效脚本。

`if_image` 根据本次图片匹配选择分支，复用已登记的图片或搜索资源。下面是一个步骤片段，其中两个搜索名需先在 `resources.searches` 中定义：

```json
{"if_image": {
  "search": "主按钮", "min_confidence": 0.9,
  "then": [{"click": {"search": "主按钮"}}],
  "else": [{"click": {"search": "备用按钮"}}]
}}
```

也可使用 `image` 引用 `resources.images`，并提供内联 `region` 和 `min_confidence`。`then` 必须非空；`else` 可省略，提供时必须非空。分支可嵌套相同的步骤。此判断不等待图片出现，需要等待时使用 `wait_until_image`；所有分支的资源引用都会在执行前检查。

`repeat.max_seconds` 可选，必须为正的有限秒数；从进入该循环起按单调时钟计算，识图耗时也计入，到期结束该层循环并继续后续步骤。嵌套循环受最早的外层期限约束；等待会裁短，输入前再次检查期限，已经进入的平台调用及清理可能稍晚返回。模拟运行以虚拟等待推进时间，无需实际等待数分钟。

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
