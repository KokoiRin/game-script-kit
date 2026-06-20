## Context

`capture-region-crops` 和 `capture-probe-crops` 都用于校准状态识别素材和区域。它们的输出目录是固定路径，因此重复运行时会混合新旧 PNG。对于状态识别调试来说，目录内容必须能代表最近一次运行，否则用户会基于过期裁剪图做错误判断。

## Goals / Non-Goals

**Goals:**

- 每次裁剪导出前删除对应输出目录下的旧 PNG。
- 只清理 Star 自己生成的裁剪图片，不删除目录里的非 PNG 文件。
- 本轮没有保存裁剪图时，输出目录中不残留旧裁剪图。

**Non-Goals:**

- 不清理原始截图、诊断框截图或其他 debug 目录。
- 不改变裁剪文件命名、输出路径、stdout 文案或 CLI 参数。
- 不新增历史版本管理；当前目录只表达最近一次导出结果。

## Decisions

- 在 application 层新增小 helper，接收输出目录并删除其直接子级 PNG 文件。
- 在 `capture_screen_region_crops` 和 `capture_screen_probe_crops` 创建输出目录后、保存本轮裁剪前调用该 helper。
- 只删除直接子文件，不递归删除，避免误删用户手动放入的子目录内容。

## Risks / Trade-offs

- 如果用户手动把 PNG 放进这些 debug 输出目录，会在下一次导出时被删除。该目录语义是 Star 生成的最近一次结果，保留手动文件不属于本轮目标。
