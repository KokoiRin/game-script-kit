## Context

脚本模型已经支持 `Script.resources`，runner 在执行 `ImageExists(ImageRef(...))` 和 `Click(ImageTarget(ImageRef(...)))` 时会通过资源目录解析图片。脚本详情当前已经返回 `image_dependencies`，但只收集直接 `ImageTemplate` 路径。

## Goals / Non-Goals

**Goals:**

- 让 `image_dependencies` 覆盖脚本资源目录中可解析的 `ImageRef`。
- 让 `click-leave-or-retry-loop` 这类命名图片脚本在 UI dry-run 中自动拿到图片命中模板。
- 保持前端和 HTTP payload 不变。

**Non-Goals:**

- 不新增从 JSON 自动加载通用脚本资源目录的能力。
- 不在脚本详情阶段改变未知图片引用的错误语义。
- 不支持动态生成图片路径或模糊名称匹配。

## Decisions

- `describe_script_details` 将脚本的 `resources` 传给图片依赖收集逻辑，遇到 `ImageRef` 时调用 `resources.resolve_image(...)` 得到 `ImageTemplate.path`。
- 如果某个 `ImageRef` 无法解析，脚本详情不会把它加入 `image_dependencies`；这避免 UI dry-run 传入错误模板，同时保留 runner 运行时的明确失败。
- 去重顺序继续按脚本阅读顺序，和直接 `ImageTemplate` 行为保持一致。

## Risks / Trade-offs

- 未知命名图片不会出现在 `image_dependencies` 中 → 依赖摘要仍会显示 `ImageRef("...")`，后续可以扩展 readiness 专门检查命名资源缺失。
- 只解析脚本自带 `resources` → 这是当前架构里最稳定的资源来源，避免 application 层额外猜测全局资源文件。
