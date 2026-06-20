## 1. OpenSpec 和测试

- [x] 1.1 添加 loader/catalog 测试，覆盖坏文件隔离、重复名称隔离和错误收集。
- [x] 1.2 添加 CLI list 测试，覆盖 stdout 保留可用脚本、stderr 展示坏脚本错误。
- [x] 1.3 添加 UI HTTP 和静态资源测试，覆盖 `script_config_errors` payload 与页面展示。

## 2. 实现

- [x] 2.1 为配置脚本 loader 增加 tolerant 加载结果，保留 strict loader 行为。
- [x] 2.2 更新项目 catalog 组装，跳过坏脚本并收集结构化配置错误。
- [x] 2.3 更新 CLI list、本地控制 application、HTTP payload 和前端展示。

## 3. 验证和归档

- [x] 3.1 运行相关测试、全量测试、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行 CLI smoke test，确认坏脚本不影响可用脚本 list/details/run。
- [x] 3.3 完成 OpenSpec 归档。
- [x] 3.4 提交并推送当前分支。
