## Context

Goal 3 已经建立图片匹配查询结果。现在需要从匹配矩形中选择点位，为后续 offset 提供稳定基础点。

## Goals / Non-Goals

**Goals:**

- 支持 `center`、`top_left`、`top_center`、`top_right`、`left_center`、`right_center`、`bottom_left`、`bottom_center`、`bottom_right`。
- `ImageTarget` 可指定 anchor，默认保持 `center`。
- runner 根据查询结果和 anchor 计算点击点。

**Non-Goals:**

- 不做 offset。
- 不做比例点位或任意公式。
- 不做匹配结果缓存。

## Decisions

### Decision 1: anchor 计算放在 ImageMatch

`ImageMatch` 已经拥有匹配矩形和中心点，按 anchor 取点是纯领域逻辑，适合放在领域值对象上。

### Decision 2: ImageTarget 保存 anchor 字符串

第一版使用明确字符串集合，便于未来从自然语言前端或外部脚本格式生成。非法 anchor 在领域模型创建时拒绝。

## Risks / Trade-offs

- [Risk] 字符串 anchor 可能拼错。→ Mitigation：创建 `ImageTarget` 或调用 `point_at` 时立即校验并返回清晰错误。
