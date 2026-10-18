# 0002：沿用 ports-and-adapters 分层

- 状态：accepted
- 日期：2026-10-18（记录并沿用既有架构原则，不推定最初决定日期）
- 性质：既有代码边界与职责取舍

## 背景

游戏规则、桌面输入、图像识别和 CLI/UI 的变化原因不同。若脚本或执行器直接依赖 macOS 与页面控制逻辑，规则测试需要真实桌面，迁移平台也会牵动业务代码。

项目已将核心置于 `portable/`，真实桌面适配置于 `platform/`。本次精简继续使用这条边界，没有理由为了删除工具重写执行引擎。

## 决定

调用沿“入口 → 应用用例 → 执行/规则 → 领域模型”推进。平台装配负责选择适配实现并注入用例，真实副作用通过 port 调用；已经装配的用例可以被入口反复使用。

领域描述不可变步骤和不变量；执行器解释步骤；应用层编排用户意图并归一化结果；入口只解析请求并展示结果。规范细节统一见 [架构约束](../architecture.md)，不在 ADR 重复维护。

新任务优先复用现有步骤和接口。只有当前实现或真实复用需要时才深化模块，不为假设中的平台和功能提前添加抽象。

## 代价

- 必须维护 port、适配实现与装配关系，简单操作也可能涉及几个职责位置。
- 分层本身不保证接口足够简单；薄转发层、重复规则和泄漏到入口的脚本语义仍需要审视。
- 核心可移植不等于新平台已经可用；Windows 等真实实现的完成状态见 [当前状态](../current-state.md)。

## 重审条件

当同一条业务规则散落到多个入口、核心开始依赖平台细节，或新任务反复要求穿透接口时，重审已触达模块的职责和接口。

调整以解决具体阻碍为范围；没有真实阻碍时，不通过目录重排证明架构改进。

## 依据

- [领域步骤](../../src/game_automation/portable/domain/actions.py)、[执行器](../../src/game_automation/portable/engine/runner.py)。
- [运行 ports](../../src/game_automation/portable/engine/ports.py)、[单脚本应用用例](../../src/game_automation/portable/application/script_run.py)。
- [本地桌面装配](../../src/game_automation/platform/local_desktop/composition.py)。
