## Context

屏幕诊断链路依赖三类能力：

- 本地项目路径和 `assets/screen-states.json` 配置读取。
- 通过注入 factory 获得截图、屏幕尺寸和图片定位能力。
- 基于 Pillow 生成诊断图片、裁剪图和黑屏警告。

这些都是 application 用例层可以编排的能力，但不应让 `LocalControlApplication` 直接持有全部实现细节。

## Goals / Non-Goals

**Goals:**
- 让 `LocalControlApplication` 成为屏幕诊断公开方法的薄 facade。
- 让 `ScreenDiagnosticsUseCase` 面向 application 语义，不暴露 Pillow、HTTP、DOM 或 CLI。
- 让诊断 artifact 处理集中在一个模块，便于单独测试图像产物行为。

**Non-Goals:**
- 不改变 CLI 子命令、HTTP endpoint 或前端 payload。
- 不拆脚本后台运行会话和界面状态探测后台会话。
- 不新增状态识别或图片匹配语义。

## Decisions

- `ScreenDiagnosticsUseCase` 接收项目路径、截图 factory、屏幕尺寸 factory、图片定位 factory，并在内部完成配置读取和状态探测。
- `diagnostic_artifacts` 只处理文件产物和 Pillow 细节，不依赖 `LocalControlApplication`、HTTP、CLI 或 platform adapter。
- `LocalControlApplication` 继续暴露原方法，避免入口层改动。

## Risks / Trade-offs

- 为保持行为不变，本轮会保留部分状态探测候选读取逻辑在本地控制 facade 中供后台探测使用，后续可再抽取状态探测 use case。
- 图像产物测试会从 facade 测试迁移到新 artifact/use case interface，减少对内部实现的绑定。
