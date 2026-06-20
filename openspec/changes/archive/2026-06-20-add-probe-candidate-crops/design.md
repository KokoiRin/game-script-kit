## Context

`capture-probe-diagnostics` 已经能把候选 `best_rect` 画到整张截图上。裁剪导出应复用同一轮探测结果和同一套屏幕坐标换算逻辑，把每个候选最佳位置转成截图像素区域并保存独立 PNG。

## Decisions

- 输出目录为 `.star/debug/screenshots/probe-crops/`。
- CLI 子命令命名为 `capture-probe-crops`，支持 `--min-confidence`，默认 `0.8`。
- 文件名包含候选序号、状态名和搜索项名，使用安全文件名转换。
- 只导出有 `best_rect` 的候选；跳过候选或无最佳位置候选不导出。
- 如果没有任何候选可裁剪，命令仍成功并输出 `no probe candidate crops saved`。

## Non-Goals

- 不在 UI 中展示多个裁剪图。
- 不自动替换或生成 `assets/*.png` 状态素材。
- 不改变 `capture-region-crops` 的行为。
