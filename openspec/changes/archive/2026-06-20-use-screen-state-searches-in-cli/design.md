# Design: use-screen-state-searches-in-cli

## Boundary

CLI 入口仍只负责参数解析、脚本查找、资源装配和结果打印；状态配置解析与资源合并放在 application helper 中。runner、domain 和 adapter 不读取项目文件。

## Shared Helper

新增 application helper：

- 读取项目 assets 路径和 `screen-states.json` 路径。
- 调用现有 `load_screen_state_target_catalog(...)`。
- 把共享 `TargetCatalog` 与脚本 `resources` 合并。

合并顺序与 UI 一致：共享资源先，脚本局部资源后；同名资源由脚本局部资源覆盖。

## CLI Error Handling

缺少 `screen-states.json` 不影响现有 CLI 脚本。配置存在但非法时，`star run` 返回配置错误，并在 stderr 报告共享资源配置失败。
