## Context

`LocalControlApplication` 已提供 `capture_screen_region_crops()` 和 `capture_screen_probe_crops()`。CLI 已有对应命令，但 UI 只暴露区域诊断图和探测诊断图。裁剪导出是状态素材调试的重要下一步，应在 UI 中作为同一组诊断动作出现。

## Goals / Non-Goals

**Goals:**

- 在 UI 诊断按钮区新增区域裁剪和候选裁剪触发入口。
- HTTP adapter 新增 POST 接口，只调用 application 层用例并复用现有 `ControlResult` payload。
- 候选裁剪沿用探测诊断的最低置信度输入。

**Non-Goals:**

- 不在 UI 中展示多个裁剪图片缩略图。
- 不新增下载 zip、打开文件夹或历史记录。
- 不改变 application 层裁剪导出文件名、目录刷新规则或 CLI 行为。

## Decisions

- 新增 `/api/capture-region-crops` 和 `/api/capture-probe-crops`。
- UI 点击按钮后把结果追加到当前日志区域；如果 application 返回 `screenshot_path`，payload 仍保留该字段，但不生成 `screenshot_url`，因为裁剪导出结果是目录不是单张图片。
- `capture-probe-crops` 请求 body 复用 `min_confidence` 字段，和 `capture-probe-diagnostics` 保持一致。

## Risks / Trade-offs

- 用户仍需要到输出目录查看裁剪图片。该限制可接受，因为本轮目标是减少命令行切换；多图预览会引入额外静态文件路由和 UI 状态管理，适合后续单独设计。
