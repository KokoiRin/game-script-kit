## 1. 文件脚本解析

- [x] 1.1 添加配置脚本 loader 测试，覆盖 `wait_until_image` 引用搜索别名和图片别名。
- [x] 1.2 实现 `wait_until_image` JSON 解析，转换为 `WaitUntil(ImageExists(...))`。

## 2. 项目脚本

- [x] 2.1 把师门、秘境和宝图脚本改为先等待任务搜索目标出现，再点击搜索结果。

## 3. 验证

- [x] 3.1 运行相关测试、全量测试、OpenSpec 校验和 diff 检查。
- [x] 3.2 用真实游戏窗口 smoke test 至少一个状态+图片等待脚本。
