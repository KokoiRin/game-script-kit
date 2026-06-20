# Design: UI 展示脚本详情预览

## Context

`ScriptCatalog` 已能按名称返回 `Script`。`LocalControlApplication` 是 UI 和脚本 catalog 之间的 application seam，适合提供“脚本详情”这种只读用例。HTTP adapter 只负责把 query 参数转成 application 调用并返回 JSON。

## Decisions

1. **详情构建放在 application 层。**
   UI 不理解 Python 脚本模型；它只展示 application 返回的可读摘要。

2. **第一版展示摘要文本，不做完整 AST 可视化。**
   脚本模型仍在演进，完整结构化编辑器会过早锁定形态。摘要足以解决“我选的脚本会做什么”的问题。

3. **依赖摘要覆盖状态、图片、点位和颜色。**
   这些是用户调脚本时最常需要确认的外部信号。重复依赖按首次出现顺序去重。

4. **未知脚本返回清晰错误。**
   application 保持 `ControlResult` 风格，HTTP endpoint 返回非零 `exit_code` 与错误文本，避免 UI 直接处理异常。

## Risks

- 摘要文本会随着脚本模型扩展而增加格式分支。先把摘要 helper 留在 application 层，后续如果变复杂再提炼为专门 presenter。
- 摘要不是可执行 DSL，不能承诺用户复制后直接运行。
