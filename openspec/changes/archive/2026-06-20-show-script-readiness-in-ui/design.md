# Design: UI 展示脚本运行前依赖检查

## Context

脚本详情当前由 `LocalControlApplication.describe_script()` 生成，已经能遍历步骤树并收集依赖摘要。依赖检查和依赖摘要使用同一份脚本遍历逻辑，适合继续放在 application 层。

## Decisions

1. **依赖检查作为脚本详情的一部分返回。**
   UI 只展示 application 返回的状态，不直接读文件或解析 `screen-states.json`。

2. **检查项使用简单结构：label/status/message。**
   `status` 只使用 `ok`、`missing`、`unknown`。这足够给 UI 做可读展示，同时不把未来校验规则锁死。

3. **状态配置不可用时标记状态依赖为 unknown。**
   缺少或非法 `screen-states.json` 不一定意味着脚本无法运行，因为脚本仍可能通过 assets 文件 fallback 做状态探测。第一版只把它展示为无法确认，而不是硬错误。

4. **图片检查只覆盖项目内 `assets/` 路径。**
   当前 UI 使用项目 assets 作为模板管理入口。其他路径的图片模板先标记为 unknown，避免越权读取任意路径。

## Risks

- 检查结果不是运行保证。运行时仍可能因为截图权限、匹配阈值或窗口位置失败。
- 状态 fallback 可能让未配置状态仍可运行，因此状态检查只作为提示。
