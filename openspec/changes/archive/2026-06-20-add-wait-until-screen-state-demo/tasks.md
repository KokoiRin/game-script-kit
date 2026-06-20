## 1. 测试

- [x] 1.1 添加默认 catalog 测试，覆盖 `wait-until-screen-state-demo` 已注册。
- [x] 1.2 添加脚本详情测试，覆盖状态等待步骤和状态依赖。
- [x] 1.3 添加 CLI dry-run 测试，覆盖 `--dry-run-screen-state 主页` 成功执行等待后动作。

## 2. 实现

- [x] 2.1 新增 `wait_until_screen_state_demo` 脚本定义模块。
- [x] 2.2 把新脚本注册到默认 catalog 和 scripts_manager 导出。
- [x] 2.3 确认脚本详情无需新增 presenter 逻辑即可展示 `WaitUntil ScreenStateIs(...)`。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 CLI smoke：`list`、`details` 和 dry-run。
- [x] 3.3 归档 OpenSpec change。
