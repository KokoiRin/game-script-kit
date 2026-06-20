## Why

状态探测现在会输出 `best_confidence` 和 `best_rect`，但用户仍需要把坐标和实际截图对应起来。为了更快判断状态素材、区域配置和真实游戏画面是否对齐，需要一张直接画出“配置区域”和“候选最佳匹配位置”的诊断图。

## What Changes

- 新增 application 用例：执行一次界面状态探测并保存探测诊断截图。
- 新增 CLI 子命令 `star capture-probe-diagnostics`。
- 本地 UI 增加“探测诊断”入口，并展示生成的诊断图。
- 诊断图展示配置命名区域和每个候选的 `best_rect`，候选标签包含状态、搜索项、命中状态和最佳置信度。

## Capabilities

### New Capabilities

- 用户可以生成一张带状态探测候选最佳匹配框的截图，用于调试素材和区域。

### Modified Capabilities

- `screen-state-probe`: 增加探测诊断截图导出能力。
- `local-control-ui`: 增加探测诊断按钮和图片预览。

## Impact

- 影响 application 层、本地 CLI、HTTP UI adapter、前端静态资源和测试。
- 不改变图片匹配阈值、状态选择规则、脚本条件语义或 `assets/screen-states.json` 格式。
