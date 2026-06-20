## 1. Application 和 HTTP

- [x] 1.1 更新 `LocalControlApplication` 同步/后台脚本运行方法，接收并传递 `dry_run_screen_state`。
- [x] 1.2 更新本地 UI HTTP adapter，解析脚本运行 payload 中的 `dry_run_screen_state`。

## 2. 前端 UI

- [x] 2.1 在脚本运行工具栏增加模拟状态输入，默认值为 `未知`。
- [x] 2.2 前端启动脚本时把模拟状态加入请求 payload。

## 3. 验证和归档

- [x] 3.1 补 application、HTTP/UI 和静态资源测试。
- [x] 3.2 运行全量测试、`git diff --check` 和 OpenSpec 严格校验。
- [x] 3.3 合并主规格、归档 change、提交并推送。
