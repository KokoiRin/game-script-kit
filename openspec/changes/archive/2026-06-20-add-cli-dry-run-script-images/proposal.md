# Change: add-cli-dry-run-script-images

## Why

CLI 用户现在可以用 `star details <name>` 看到脚本的图片依赖，但验证图片成功路径时仍要把这些路径手动逐个复制为 `--dry-run-image`。对于使用 `SearchRef(...)` 和 `screen-states.json` 的脚本，这一步很机械，也容易写错路径。

## What Changes

- 给 `star run` 增加 `--dry-run-script-images` 开关。
- 开启后，CLI 在 dry-run 模式下把脚本详情解析出的 `image_dependencies` 自动加入 dry-run 命中图片。
- 默认 dry-run 行为保持不变：未指定图片时仍表示图片不存在。

## Impact

- Affected specs: `script-management`
- Affected code: CLI entrypoint, CLI tests
