## Why

Star 的长期目标是让脚本能根据当前识别到的游戏界面状态决定下一步动作。当前状态探测只能在 UI 中观察，脚本仍然只能直接判断颜色或图片，无法把“当前是主页/人物/战斗失败”作为一等条件使用。

## What Changes

- 新增脚本条件 `ScreenStateIs`，用于判断当前界面状态是否等于指定状态名称。
- 引擎通过新的 `ScreenStateReader` port 获取当前状态，保持平台无关，不直接读取 `assets/screen-states.json`。
- 本地控制 application 把已有 `probe_screen_state_once` 能力包装成脚本运行时的状态读取端口。
- 增加一个可 dry-run 验证的示例脚本，展示状态条件如何驱动分支。

## Capabilities

### New Capabilities

### Modified Capabilities
- `game-script-core`: 脚本条件支持根据当前界面状态执行分支和等待。

## Impact

- 影响领域条件模型、条件评估器、runner 端口注入和脚本需求分析。
- 影响本地控制 application 的真实脚本运行装配。
- 增加脚本 catalog 中的状态条件示例。
- 不新增运行时第三方依赖。
