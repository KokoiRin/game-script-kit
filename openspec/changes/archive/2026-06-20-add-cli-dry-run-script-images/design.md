# Design: add-cli-dry-run-script-images

## Boundary

CLI 不直接遍历脚本步骤。它复用 `describe_script_details(...)` 生成的 `image_dependencies`，再把这些路径传给 `run_script_on_local_desktop(...)` 的 `dry_run_images` 参数。

## Behavior

`--dry-run-script-images` 只在 `--dry-run` 下有意义：

- 未开启时，现有 `--dry-run-image` 行为保持不变。
- 开启时，最终 dry-run 图片集合为用户显式传入图片与脚本图片依赖的去重并集。
- 若脚本图片依赖不可解析，沿用现有详情逻辑：未知依赖不会进入 `image_dependencies`，运行时仍可能按找不到图片或未知资源失败。

## Error Handling

如果用户在非 dry-run 模式使用该开关，CLI 返回配置错误。真实运行不应受 dry-run 模拟图片设置影响。
