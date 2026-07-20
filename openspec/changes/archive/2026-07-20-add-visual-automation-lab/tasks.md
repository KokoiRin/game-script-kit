## 1. 状态机

- [x] 1.1 为正常流程、非法动作、加载延迟和目标缺失模式添加行为测试。
- [x] 1.2 实现独立 `TaskFlowScenario`、状态快照和事件模型。

## 2. HTTP 靶场

- [x] 2.1 为页面、状态、事件、动作和重置接口添加 HTTP contract 测试。
- [x] 2.2 实现标准库 HTTP server、JSON 错误映射和静态资源读取。
- [x] 2.3 实现原生 HTML/CSS/JavaScript 页面和稳定视觉目标资源。

## 3. 启动与使用

- [x] 3.1 添加 `star-lab` console script 和参数测试。
- [x] 3.2 更新 README，说明靶场启动、故障模式和真值验收方式。

## 4. 验证

- [x] 4.1 运行靶场相关测试和 HTTP 完整流程 smoke。
- [x] 4.2 运行全量 pytest、`openspec validate --specs --strict` 和 `git diff --check`。
- [x] 4.3 严格校验并归档 `add-visual-automation-lab`。
