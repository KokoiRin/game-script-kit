## Coordinate Model

截图图片在浏览器中可能被缩放展示，真实 macOS 又可能存在 Retina 像素和鼠标坐标点的差异。UI 必须分三层处理：

- 浏览器显示坐标：用户鼠标拖拽的位置。
- 截图像素坐标：根据 `img.naturalWidth/naturalHeight` 换算。
- 脚本区域坐标：根据 application 返回的 `screen_size` 换算到脚本和图像定位 adapter 使用的坐标系。

如果后端没有返回 `screen_size`，UI 退化为使用截图像素坐标，但需要明确展示当前换算依据。

## Preview Matching

预览匹配是只读诊断能力，不执行点击，也不修改脚本文件。HTTP handler 只解析 payload 并调用 application。application 委托 `ScreenDiagnosticsUseCase`：

- 校验素材路径位于 `assets/`。
- 校验区域是正向矩形。
- 通过注入的 `ScreenImageLocator` 以该区域和最低置信度执行一次匹配。
- 返回结构化结果和 stdout 日志，供 UI 展示。

## Out of Scope

- 本轮不自动写入 `scripts/*.json` 或 `assets/screen-states.json`。
- 本轮不提供多区域管理、命名区域保存或图片裁剪保存。
- 本轮不改变脚本 DSL。
