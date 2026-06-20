## Context

底层 `run_script(...)` 已经根据脚本需求决定是否创建真实 `ScreenStateReader`。当前缺口在平台装配层：`run_script_on_local_desktop(...)` 没有传入 `real_screen_state_reader_factory`。

`LocalControlApplication` 已经封装了状态配置读取、图像定位 adapter 和后台探测复用逻辑。CLI 真实运行状态条件脚本时应复用这条 application 路径，而不是在 CLI 入口层创建图像定位或解释状态识别规则。

## Decisions

- 在 local desktop composition 中新增真实状态 reader factory。
- 该 factory 通过 `LocalControlApplication` 创建已有状态 reader。
- `run_script_on_local_desktop(...)` 将该 factory 传给 `run_script(...)`。
- `run_script(...)` 仍按脚本需求懒加载 reader；不含状态条件的脚本不会实际创建状态 reader。

## Non-Goals

- 不新增 CLI 参数。
- 不改变 dry-run 状态来源。
- 不改变状态探测候选加载、匹配策略或缓存策略。
