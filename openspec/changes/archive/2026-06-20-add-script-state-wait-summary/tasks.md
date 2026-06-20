## 1. 测试

- [x] 1.1 添加 application 层脚本详情测试，覆盖 `WaitUntil(ScreenStateIs(...))` 会进入 `state_waits`。
- [x] 1.2 添加 CLI details 测试，覆盖“状态等待”分组和 `等待状态: 主页`。
- [x] 1.3 添加 UI HTTP payload 测试，覆盖 `/api/script-details` 返回 `state_waits`。
- [x] 1.4 添加 UI 静态脚本测试，覆盖状态等待分组和当前探测状态预览文本。

## 2. 实现

- [x] 2.1 在 `ScriptDetailsResult` 中新增 `state_waits` 字段。
- [x] 2.2 在 `script_details` presenter 中递归收集 `WaitUntil(ScreenStateIs(...))`。
- [x] 2.3 在 CLI details 输出中新增“状态等待”分组。
- [x] 2.4 在 UI HTTP payload 中序列化 `state_waits`。
- [x] 2.5 在本地 UI 脚本详情中展示状态等待和当前满足情况。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 CLI smoke：`star details wait-until-screen-state-demo`。
- [x] 3.3 归档 OpenSpec change。
