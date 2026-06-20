## Context

`TargetCatalog` 已有 `NamedImageSearch`、`ImageSearchSpec` 和 `SearchRef`，能把图片、区域和最低置信度收拢成命名搜索规格。状态识别配置已经使用这套模型，但脚本动作和条件还没有消费它，导致同一搜索参数仍要在脚本里重复书写。

## Goals / Non-Goals

**Goals:**

- 让 `ImageExists(SearchRef("..."))` 判断命名搜索是否存在。
- 让 `Click(ImageTarget(SearchRef("...")))` 点击命名搜索结果。
- 复用 `TargetCatalog.resolve_search()`，保持图片、区域和置信度解析集中。
- 让脚本详情和 UI dry-run 依赖能看到搜索别名解析出的图片路径。

**Non-Goals:**

- 不新增 JSON/YAML 脚本格式。
- 不实现多匹配选择或批量搜索 DSL。
- 不改变状态识别配置文件格式。

## Decisions

- 将图片查询解析集中到 `image_query.locate_image()`。
  - 理由：条件和图片目标点击都需要同样的搜索别名解析，集中后避免两处规则漂移。

- `ImageExists` 和 `ImageTarget` 的 `min_confidence` 使用 `None` 表示“使用搜索规格默认值”。
  - 理由：现有默认 `1.0` 无法区分用户显式覆盖和未提供参数。最终调用 locator 时，如果搜索规格也没有置信度，仍使用 `1.0`。

- 脚本步骤显式 `region` 优先于搜索规格里的 `region`。
  - 理由：别名提供默认搜索范围，但局部脚本有时需要临时缩小范围。

## Risks / Trade-offs

- `min_confidence` 类型从 `float` 扩展为 `float | None` → 通过最终查询默认值保持旧脚本行为不变，并更新展示逻辑。
- `ImageTarget.template` 字段名在支持 `SearchRef` 后语义变宽 → 当前先保持字段名兼容，避免大范围重命名；后续若引入脚本前端再统一命名。
