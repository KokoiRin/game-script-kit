# Change: UI 展示脚本运行前依赖检查

## Why

脚本详情已经能展示步骤和依赖，但用户仍需要自己判断这些依赖是否已经准备好。例如图片脚本需要 `assets/start.png`，状态脚本需要 `assets/screen-states.json` 中配置 `主页`。缺少依赖时，用户往往要运行脚本后才从日志里发现问题。

这一步在脚本详情里加入运行前依赖检查，让用户在点击运行之前就能看到关键资源是否可用。

## What Changes

- application 层的脚本详情结果增加依赖检查项。
- 第一版检查：
  - `ImageTemplate("assets/...")` 对应文件是否存在且后缀受支持。
  - `ScreenStateIs("...")` 对应状态名是否出现在 `assets/screen-states.json` 配置中。
- UI 在脚本详情中展示依赖检查结果。

## Impact

- 修改能力：`local-control-ui`
- 不改变脚本执行语义，不阻止用户运行脚本。
- 不检查点位别名和颜色读数是否真实可用；它们继续只作为依赖摘要展示。
