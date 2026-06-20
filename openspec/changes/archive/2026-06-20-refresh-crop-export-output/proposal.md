## Why

状态区域裁剪和探测候选裁剪都写入固定 debug 目录。配置变化、候选数量减少或本轮没有可裁剪候选时，旧 PNG 可能继续留在目录中，用户会误以为它们属于本轮导出结果。

## What Changes

- 每次执行区域裁剪导出前，刷新 `.star/debug/screenshots/regions/` 中的旧 PNG。
- 每次执行探测候选裁剪导出前，刷新 `.star/debug/screenshots/probe-crops/` 中的旧 PNG。
- 本轮没有可保存裁剪图时，输出目录也只保留本轮结果，也就是不保留上一次的旧 PNG。

## Capabilities

### New Capabilities

### Modified Capabilities

- `screen-state-probe`: 裁剪导出目录改为表示最近一次导出结果，避免旧裁剪图误导调试。

## Impact

- 影响 application 层裁剪导出用例和测试。
- 不改变截图、图片匹配、状态选择、CLI 参数、UI 行为或输出目录路径。
