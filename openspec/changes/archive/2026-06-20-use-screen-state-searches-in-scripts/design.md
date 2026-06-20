# Design: use-screen-state-searches-in-scripts

## Boundary

共享搜索资源属于本地控制 application 组装职责。领域模型、runner 和 image locator 不读取 `screen-states.json`，也不感知 assets 目录。

## Resource Merge

读取 `assets/screen-states.json` 时复用现有状态配置解析规则：

- `regions` 转成 `NamedRegion`。
- 每个 `groups[].searches[]` 转成 `NamedImageSearch`。
- 图片路径解析为 assets 下的 `ImageTemplate` 绝对路径。

合并顺序为共享资源先、脚本资源后。若同名点位、图片、区域或搜索同时存在，脚本资源覆盖共享资源。这样脚本可以临时覆盖某个搜索项，不会被全局状态配置反向改变。

## Error Handling

缺少 `screen-states.json` 时不影响现有脚本行为。配置非法时：

- `describe_script` 返回配置错误，避免 UI 误报依赖。
- `run_named_script` 和 `start_named_script` 返回 setup/configuration 错误，不进入 runner。
