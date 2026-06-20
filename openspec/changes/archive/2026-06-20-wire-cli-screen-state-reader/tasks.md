## 1. 规格与测试

- [x] 1.1 补充 `script-management` 规格，定义 CLI 真实运行状态条件脚本时的状态 reader 装配要求。
- [x] 1.2 添加 composition 行为测试，复现 `run_script_on_local_desktop` 未传状态 reader factory 的缺口。

## 2. 实现

- [x] 2.1 为本地控制 application 暴露可复用的状态 reader factory 方法。
- [x] 2.2 在 local desktop composition 中提供真实状态 reader factory。
- [x] 2.3 让 `run_script_on_local_desktop` 把状态 reader factory 注入 `run_script(...)`。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
