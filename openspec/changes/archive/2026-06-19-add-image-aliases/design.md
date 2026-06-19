## Context

Goal 1 已经引入 `NamedPoint`、`PointRef` 和 `TargetCatalog`，并让 `Script` 携带资源目录。本轮在同一目录中加入图片资源分支，使图片别名和点位别名使用同一个 portable 资源入口。

## Goals / Non-Goals

**Goals:**

- 提供 `NamedImage` 和 `ImageRef`。
- 让 `TargetCatalog` 可以解析图片引用为 `ImageTemplate`。
- 让 `ImageExists(ImageRef(...))` 和 `ImageTarget(ImageRef(...))` 保持合法。
- 让条件评估、图片点击和脚本需求分析在执行时解析命名图片。

**Non-Goals:**

- 不做匹配结果变量或查询对象。
- 不做 anchor 和 offset。
- 不做模板文件管理 UI 或外部配置。

## Decisions

### Decision 1: 复用 TargetCatalog

图片别名和点位别名都是脚本资源，使用同一个 `TargetCatalog` 可以让 `Script.resources` 保持一个入口。后续 offset 或 anchor 不需要再增加新的脚本字段。

### Decision 2: port 仍只接收 ImageTemplate

`ScreenImageLocator` 是平台端口，不应该理解别名。engine 在调用 port 前把 `ImageRef` 解析为 `ImageTemplate`。

### Decision 3: ImageRef 不等价于一次匹配

本轮只让 `ImageRef` 表达模板引用。图片是否存在、是否点击、找不到怎么办，仍由 `ImageExists`、`ImageTarget`、`If`、`WaitUntil` 和 `Click` 组合表达。

## Risks / Trade-offs

- [Risk] `point_aliases.py` 名称开始偏窄。→ Mitigation：本轮保持文件名不变以减少改动；如果后续资源类型继续增加，再用单独 change 重命名为更通用模块。
- [Risk] 条件和 runner 都需要解析图片引用，可能重复逻辑。→ Mitigation：先用 `TargetCatalog.resolve_image` 收敛名称解析，后续匹配查询 change 再抽统一查询函数。
