# Change: add-script-details-cli

## Why

用户写脚本时需要快速知道某个脚本有哪些步骤、依赖哪些状态和图片、dry-run 需要哪些图片模板。目前这些信息只在 UI 脚本详情里可见，CLI 用户只能直接运行脚本，失败后再猜缺了什么。

## What Changes

- 增加 `star details <name>` 子命令。
- CLI 详情输出复用 application 层 `describe_script_details`，展示步骤、依赖、图片依赖和 readiness。
- 详情读取前复用共享脚本资源装配，使 `assets/screen-states.json` 中的搜索别名也能被解析。

## Impact

- Affected specs: `script-management`
- Affected code: CLI entrypoint, CLI tests
