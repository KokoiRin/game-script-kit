## Why

编写游戏脚本时需要快速获取屏幕坐标，并把有用的位置记录下来。当前项目已经有 `Point` 领域模型，但还缺少一个独立的小工具帮助用户在真实桌面环境中采集坐标。

## What Changes

- 新增一个独立坐标记录工具，用于实时读取鼠标当前位置。
- 新增坐标读取端口，由平台 adapter 负责实现真实鼠标坐标读取。
- 工具每 1 秒打印一次当前坐标。
- 用户按下 `1` 时记录当前坐标。
- 用户按下 `Q` 或 `q` 时结束工具。
- 工具结束后打印本次记录的所有坐标。
- 该工具与现有 `Script`、`ScriptRunner` 和 demo CLI 流程分离，不改变脚本执行语义。

## Capabilities

### New Capabilities

- `coordinate-recorder-tool`: 定义独立坐标记录工具的交互行为、输出和边界。

### Modified Capabilities

无。

## Impact

- 新增独立工具入口和工具实现模块。
- 复用现有 `Point` 领域模型表达当前坐标和记录坐标。
- 通过 port-and-adapter 结构读取鼠标坐标和键盘状态；真实实现可使用 `pyautogui.position()` 和轻量键盘输入库。
- 不新增 `GetCoordinate` 脚本 action，不影响 `Script`、`ScriptRunner`、`InputDevice` 或现有 demo。
