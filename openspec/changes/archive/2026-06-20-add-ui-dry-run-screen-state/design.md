## Context

`run_script` 已经支持 `dry_run_screen_state`，CLI 也已经通过 `--dry-run-screen-state` 暴露该参数。本地 UI 仍只暴露 dry-run 颜色和图片相关控制，导致用户无法直接在 UI 中验证状态条件脚本的不同分支。

## Goals / Non-Goals

**Goals:**
- 在 UI 中提供一个简单文本输入，用于设置 dry-run 当前状态。
- HTTP adapter 只解析 payload 并委托 application 层。
- application 层把该参数传给 `run_script`，保持脚本执行语义集中在现有用例中。

**Non-Goals:**
- 不自动从 `screen-states.json` 生成下拉选项。
- 不在 UI 中分析脚本是否包含 `ScreenStateIs`。
- 不改变真实运行时的状态探测逻辑。
- 不新增状态缓存或状态编辑 UI。

## Decisions

1. **先用文本输入而不是下拉。**
   当前状态配置格式还在演进，状态列表可能来自配置，也可能未来来自项目资源 catalog。文本输入成本低，也和 CLI 参数一致。

2. **默认值为 `未知`。**
   这与状态探测未知状态一致；不使用状态条件的脚本不受影响，使用状态条件的脚本默认会走非目标状态路径。

3. **application 方法显式接收 `dry_run_screen_state`。**
   这样 HTTP adapter 不需要知道 `run_script` 的内部细节，也方便测试同步运行和后台运行两条路径。

## Risks / Trade-offs

- [Risk] 用户手输状态名可能拼错。→ Mitigation: 后续可基于状态配置补下拉或自动补全；本轮先保持轻量。
- [Risk] 工具栏控件更多。→ Mitigation: 当前只增加一个短输入，后续 UI 分组时再整理布局。
