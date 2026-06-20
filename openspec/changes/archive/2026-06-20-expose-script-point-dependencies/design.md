## Context

`PointRef` 已经是脚本可以引用的命名点位模型，`script_dependencies` 也会在通用依赖文本里生成 `点位: <name>`。但脚本详情目前只有结构化 `state_dependencies` 和 `image_dependencies`，没有 `point_dependencies`，导致 CLI/UI 无法单独展示和后续复用点位依赖。

## Goals / Non-Goals

**Goals:**

- application 层脚本详情返回结构化点位依赖。
- CLI 和 UI 都展示点位依赖分组。
- 保持点位依赖收集递归覆盖 `Click`、`If`、`Repeat`、`WaitUntil` 中可达的 `PointRef`。

**Non-Goals:**

- 不新增点位配置编辑 UI。
- 不检查命名点位是否已配置；本轮只暴露依赖名称。
- 不把裸 `Point(x, y)` 归入点位依赖。
- 不改变脚本执行或 dry-run 行为。

## Decisions

1. **在 `ScriptDependencyDetails` 和 `ScriptDetailsResult` 中新增 `point_dependencies`。**
   - 理由：与 `state_dependencies`、`image_dependencies` 对齐，供 CLI/UI 入口直接转发和展示。
   - 备选：继续依赖通用 `dependencies` 文本。这样 UI 后续必须解析文本，违反入口层保持薄的约束。

2. **点位依赖只收集 `PointRef`。**
   - 理由：`PointRef` 是用户可管理的别名资源；裸坐标只是脚本字面量，不属于素材/别名管理对象。

3. **暂不做点位 readiness。**
   - 理由：当前点位可能来自脚本本地资源，后续还会有共享点位配置；本轮先把结构化依赖链路打通，避免提前设计点位配置来源。

## Risks / Trade-offs

- [Risk] 用户看到点位依赖但还不能在 UI 里编辑点位。→ Mitigation：这是后续点位管理 UI 的前置能力；本轮只解决可见性。
- [Risk] 通用依赖和点位依赖会重复展示同一个名称。→ Mitigation：当前状态/图片依赖也采用通用依赖 + 结构化分组的方式，保持一致。
