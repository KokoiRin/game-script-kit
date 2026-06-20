## 1. Application 行为

- [x] 1.1 为 `LocalControlApplication` 增加状态区域诊断截图用例，复用现有截图能力并保存诊断图。
- [x] 1.2 为缺少截图能力、缺少配置、配置非法或没有命名区域补错误路径测试。

## 2. UI 接入

- [x] 2.1 增加 HTTP endpoint，把区域诊断请求委托给 application 层并返回可预览图片 URL。
- [x] 2.2 在本地控制 UI 中增加区域诊断按钮，点击后展示诊断图和输出信息。

## 3. 验证

- [x] 3.1 运行相关 application/UI 测试和 `git diff --check`。
- [x] 3.2 运行 `openspec validate add-screen-region-diagnostics --strict` 和 `openspec validate --specs --strict`。
- [x] 3.3 使用本机 UI 服务执行一次区域诊断 smoke，确认可生成图片。
