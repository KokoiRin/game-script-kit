## 1. 领域与引擎

- [x] 1.1 新增 `ScreenStateIs` 条件模型和不变量测试。
- [x] 1.2 新增 `ScreenStateReader` port，并让条件评估器支持状态条件。
- [x] 1.3 更新 `ScriptRunner` 和脚本需求分析，确保状态条件可用于 `If` / `WaitUntil`。

## 2. Application 装配

- [x] 2.1 更新 `run_script` 支持 dry-run 固定状态 reader 和真实状态 reader factory。
- [x] 2.2 更新 `LocalControlApplication`，把现有状态探测包装成真实状态 reader。

## 3. 示例与验证

- [x] 3.1 增加一个状态条件 demo 脚本并注册到 catalog。
- [x] 3.2 运行相关测试、全量测试和 `git diff --check`。
- [x] 3.3 运行 `openspec validate add-screen-state-script-condition --strict` 和 `openspec validate --specs --strict`。
