## 1. CLI 行为测试

- [x] 1.1 补充图片目标脚本自动 dry-run 图片依赖测试。
- [x] 1.2 补充搜索别名自动 dry-run 图片依赖测试。
- [x] 1.3 补充非 dry-run 使用开关的配置错误测试。

## 2. 实现

- [x] 2.1 给 `star run` 增加 `--dry-run-script-images` 参数。
- [x] 2.2 复用脚本详情 `image_dependencies` 生成 dry-run 图片集合。
- [x] 2.3 保持默认 dry-run 图片未找到行为不变。

## 3. 验证和收尾

- [x] 3.1 运行相关测试、全量测试和 OpenSpec 校验。
- [x] 3.2 归档 OpenSpec change，提交并推送本轮修改。
