## 1. Batch Port

- [x] 1.1 新增批量图片匹配结果值对象和 `ScreenImageBatchLocator` port，并用测试覆盖输入顺序映射。
- [x] 1.2 更新界面状态探测 engine，优先使用 batch locator，保留单图 fallback。

## 2. Desktop Adapter

- [x] 2.1 为 `PyAutoGuiScreenImageLocator` 增加 `locate_many(...)`，确保一次调用只截图一次并匹配多张模板。
- [x] 2.2 增加 adapter 测试覆盖一次截图、多结果顺序和 batch 日志。

## 3. UI 装配

- [x] 3.1 更新 local desktop composition 和 application 构造参数，让 UI 界面探测路径注入 batch locator。
- [x] 3.2 增加 application 测试证明 UI 探测使用 batch locator 而不是逐个单图定位。

## 4. 验证和归档

- [x] 4.1 运行聚焦测试、完整 pytest、OpenSpec strict 校验和 `git diff --check`。
- [x] 4.2 归档 OpenSpec change，按项目规则提交并 push。
