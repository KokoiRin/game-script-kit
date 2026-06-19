## Why

现有图片识别能力只能围绕单个脚本条件或单次点击使用，无法直接回答“当前游戏处于哪个界面”。用户需要一个可观察的界面状态探测工具，持续按素材判断当前画面，并在 UI 中看到每轮匹配结果和耗时。

## What Changes

- 新增平台无关的界面状态探测能力：一轮探测对多个候选界面素材执行匹配，并输出当前状态、每个候选的命中情况、置信度和耗时。
- 本轮先使用 `assets/` 中的图片文件作为候选界面，每张图片默认代表一个同名界面状态。
- 本地控制 UI 新增“界面探测”tab，允许用户启动/停止每轮结束后再继续的循环探测，并持续展示最新状态和日志。
- 不改变现有脚本 DSL，不把状态探测塞进 `ScriptRunner`。

## Capabilities

### New Capabilities
- `screen-state-probe`: 定义通过多张模板图片识别当前界面状态的一轮探测结果和循环探测语义。

### Modified Capabilities
- `local-control-ui`: 新增界面探测 tab、启动/停止探测接口以及探测结果展示行为。

## Impact

- 新增 portable 层状态探测领域模型和 application 用例。
- 复用现有 `ScreenImageLocator`、`ImageTemplate`、图片资源目录和本地 UI HTTP server。
- UI 增加一个 tab、若干 API endpoint 和状态轮询逻辑。
- 测试覆盖 application 行为、HTTP 映射和页面可见入口。
