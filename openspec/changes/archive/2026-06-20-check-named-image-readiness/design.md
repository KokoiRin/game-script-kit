## Context

`script_details.py` 现在同时生成可读依赖摘要、结构化 `image_dependencies` 和 readiness。结构化图片依赖已经使用 `Script.resources` 解析 `ImageRef`，但 readiness 仍从 `图片: ...` 文案中提取路径，导致命名图片无法被正确检查。

## Goals / Non-Goals

**Goals:**

- readiness 检查复用脚本资源目录解析 `ImageRef`。
- 保持 `dependencies` 展示文案不变。
- 让命名图片的“已配置但文件缺失”和“命名资源未配置”可区分为用户可理解的缺失状态。

**Non-Goals:**

- 不新增前端样式或字段。
- 不改变 `image_dependencies` 的含义。
- 不引入通用资源配置文件加载。

## Decisions

- 在 application presenter 内部使用结构化收集逻辑生成 image readiness 条目，避免从展示文案反推路径。
- readiness label 继续使用用户看到的依赖标签，例如 `图片: ImageRef("离开")`，message 补充解析后的资源路径或命名资源缺失原因。
- 状态 readiness 暂时保持现有逻辑；本轮只处理图片资源检查。

## Risks / Trade-offs

- `script_details.py` 继续承担多类脚本详情收集逻辑 → 本轮只做局部收拢，后续如果继续扩展变量和资源检查，可再拆成依赖检查 presenter。
