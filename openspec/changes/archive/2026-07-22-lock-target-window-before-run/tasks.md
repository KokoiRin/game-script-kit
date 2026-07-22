## 1. Window 搜索范围

- [x] 1.1 为 ScreenWindow 和 AreaWindow 的默认及显式搜索区域添加领域测试。
- [x] 1.2 实现 `Window.resolve_region`，让条件和图片目标共用该规则。

## 2. 应用层窗口绑定

- [x] 2.1 为激活后选窗、脚本副本绑定、选窗失败和 dry-run 无副作用添加测试。
- [x] 2.2 新增 `ApplicationWindowController` port，并在 runner 创建前绑定目标 `AreaWindow`。

## 3. macOS 与入口

- [x] 3.1 为标题唯一匹配、缺失、歧义、Raise 失败和矩形转换添加 adapter 测试。
- [x] 3.2 实现 macOS AppKit + Accessibility window controller，并通过 composition 注入。
- [x] 3.3 为 `run`、`run-plan` 增加 `--target-window-title` 和参数校验。

## 4. 靶场验收

- [x] 4.1 更新视觉靶场 smoke，传入目标窗口标题。
- [x] 4.2 在错误应用前台和多个 Safari 顶层窗口下完成真实 smoke。

## 5. 验证

- [x] 5.1 运行全量 pytest、严格 OpenSpec 校验和 `git diff --check`。
- [x] 5.2 归档 change 并提交完整功能。
