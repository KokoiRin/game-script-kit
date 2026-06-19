## Context

当前 `condition_evaluator` 和 `runner` 都会直接调用 `ScreenImageLocator.locate`。随着命名图片、anchor 和 offset 增加，直接调用会让“解析图片引用、处理未找到、读取匹配结果”的逻辑分散。本轮先建立一个 portable 查询层。

## Goals / Non-Goals

**Goals:**

- 提供 `ImageLookupResult`，表达 found/not found。
- 提供 `locate_image` helper，解析命名图片并调用 `ScreenImageLocator`。
- 让条件评估和图片目标点击复用 helper。

**Non-Goals:**

- 不缓存匹配结果。
- 不提供 anchor 选择。
- 不提供 offset。
- 不改变 `ScreenImageLocator` port contract。

## Decisions

### Decision 1: 查询结果是领域值对象

`ImageLookupResult` 只包装 `ImageMatch | None`，提供 `found`、`rect`、`center` 和 `confidence` 访问。它不调用平台、不读取文件，适合放在领域层。

### Decision 2: 查询执行放在 engine

`locate_image` 需要使用 `ScreenImageLocator` port 和 `TargetCatalog`，属于执行规则层。它不创建 adapter，只消费注入端口。

## Risks / Trade-offs

- [Risk] 现在引入查询层看起来比直接调用多一层。→ Mitigation：下一轮 anchor/offset 会复用它，避免 runner 和 condition evaluator 重复扩展。
- [Risk] 找不到时属性返回 `None` 可能被误用。→ Mitigation：测试覆盖 found false，调用方仍根据语义决定继续、返回假或报错。
