# Change: use-screen-state-searches-in-scripts

## Why

`SearchRef(...)` 已经能让脚本用搜索别名表达图片匹配，但目前这些别名仍需要写在脚本代码的 `TargetCatalog` 里。用户真正维护素材和区域时，更自然的位置是 `assets/screen-states.json`：同一个搜索项既能用于界面状态探测，也能被脚本直接复用。

## What Changes

- 本地控制 application 从 `assets/screen-states.json` 构建共享 `TargetCatalog`。
- UI 运行、后台运行和脚本详情在处理脚本前合并共享资源与脚本资源。
- 脚本自身资源覆盖共享资源，保持局部脚本语义稳定。

## Impact

- Affected specs: `local-control-ui`
- Affected code: screen state config loader, local control application, local control tests
