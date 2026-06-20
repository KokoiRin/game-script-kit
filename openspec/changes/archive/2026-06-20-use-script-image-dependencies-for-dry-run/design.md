## Context

当前 `run_script` 和 CLI 已经支持 `dry_run_images`，dry-run 图像定位器会把传入模板视为已命中。UI 脚本运行路径还没有把图片依赖传进去，因此 `WaitUntil(ImageExists(...))` 和 `Click(ImageTarget(...))` 在 UI dry-run 中默认表现为未找到。

上一轮已为状态依赖增加 `state_dependencies` 结构化字段。本轮沿用同一模式，避免前端解析 `dependencies` 展示文案。

## Goals / Non-Goals

**Goals:**

- 脚本详情提供结构化 `image_dependencies`。
- UI dry-run 运行脚本时自动提交当前脚本的图片依赖作为 dry-run 图片命中模板。
- 保持真实运行语义不变。

**Non-Goals:**

- 不新增图片依赖选择 UI。
- 不改变 dry-run 图像定位器的匹配坐标规则。
- 不支持把命名图片引用反向解析成 assets 路径；本轮只对可直接作为 `ImageTemplate` 路径的依赖生效。

## Decisions

- 在 `ScriptDetailsResult` 中增加 `image_dependencies` 字段，值使用脚本运行可直接消费的图片模板路径字符串。
- 前端在加载脚本详情后缓存 `payload.image_dependencies`，运行脚本时随请求提交 `dry_run_images`。
- `LocalControlApplication` 只在 dry-run 模式下把 `dry_run_images` 传给 `run_script`，真实运行忽略该列表，避免 UI 请求影响真实匹配。

## Risks / Trade-offs

- 命名图片引用当前只能显示为 `ImageRef("...")`，不能自动转成文件路径 → 后续可以在脚本资源目录稳定后补资源解析；本轮不扩大资源装配范围。
- 自动把全部图片依赖视为命中会偏向验证成功路径 → 这符合 UI 快速调试常用路径；失败路径仍可通过不提供图片依赖的 CLI 或后续 UI 选项覆盖。
