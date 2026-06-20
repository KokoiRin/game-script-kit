# Change: use-screen-state-searches-in-cli

## Why

脚本现在可以通过 `SearchRef(...)` 引用 `assets/screen-states.json` 中的搜索别名，但这个能力只在本地 UI 路径中成立。用户用 `star run` 验证或运行同一份脚本时，会遇到同名搜索别名无法解析的问题，导致脚本语义依赖入口。

## What Changes

- 抽出共享脚本资源装配 helper，供 UI 和 CLI 共用。
- `star run` 在运行脚本前加载 `assets/screen-states.json` 中的搜索资源。
- 保持脚本自身 resources 覆盖共享资源的规则。

## Impact

- Affected specs: `script-management`
- Affected code: CLI entrypoint, application resource helper, local control application
