## Context

`assets/screen-states.json` 已经是界面状态识别的配置来源，`ScreenStateIs` 条件也已经能在脚本中使用状态名。UI 的 dry-run 模拟状态输入目前是自由文本，缺少从配置中读取状态名的辅助。

## Goals / Non-Goals

**Goals:**
- 从现有状态配置中读取去重后的状态名列表。
- 通过 HTTP 接口暴露给本地 UI。
- 前端把状态名作为 `datalist` 候选，不限制用户继续输入临时状态名。

**Non-Goals:**
- 不实现状态配置编辑器。
- 不实现自动补全组件或复杂选择器。
- 不改变状态配置 schema。
- 不改变真实状态探测流程。

## Decisions

1. **列表能力放在 application 层。**
   application 已经负责读取项目 assets 和状态配置。HTTP adapter 只返回 JSON，UI 只渲染候选项，避免入口层解析配置。

2. **缺少配置时返回空列表。**
   没有 `screen-states.json` 时，UI 仍应能运行普通脚本和手动输入模拟状态。空列表比错误更符合辅助输入的性质。

3. **保持自由文本输入。**
   `datalist` 提供建议，但不把状态名限制成配置中的枚举。这样 dry-run 可以先写脚本，再补配置。

## Risks / Trade-offs

- [Risk] 配置非法时状态候选接口返回错误会影响 UI 初始化。→ Mitigation: application 返回空列表并把错误留给状态探测/区域诊断等强依赖配置的功能报告。
- [Risk] 状态名列表只来自配置，不含 assets fallback 状态。→ Mitigation: 第一版面向长期配置化状态识别；后续可扩展为“候选状态来源摘要”。
