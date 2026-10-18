# 架构决策索引

ADR 保存重要设计取舍的状态、理由和代价。下表收录当前已采纳的决定；日期表示本次记录或确认日期，记录既有原则时会明确说明，不据此推定过去的决定时间。

## 从哪里读

- 了解项目目标和协作方式：先读 [CONTEXT](../../CONTEXT.md)，再读 [0001](0001-agent-authored-tasks.md)。
- 修改源码或接口：先读 [架构约束](../architecture.md)，需要理由时读 [0002](0002-ports-and-adapters.md) 和 [0003](0003-results-and-verification.md)。
- 判断控制台该保留什么：读 [0004](0004-small-console.md)，具体已实现范围看 [当前状态](../current-state.md)。
- 整理仓库资料：读 [0005](0005-repository-documentation.md) 和 [文档导航](../README.md)。
- 讨论循环失败恢复：读 [局部恢复设计稿](../design/local-recovery.md)；它尚未成为已采纳决策。
- 创建任务、选择脚本和资源数据根、整理框架分支：读 [0006](0006-local-task-workspaces.md)。

| 编号 | 状态 | 决策 | 来源 |
| --- | --- | --- | --- |
| [0001](0001-agent-authored-tasks.md) | accepted | 一款游戏的日常任务闭环，由用户描述、Agent 生成维护 | 本轮用户确认 |
| [0002](0002-ports-and-adapters.md) | accepted | 沿用 ports-and-adapters 分层 | 记录既有架构原则 |
| [0003](0003-results-and-verification.md) | accepted | 执行结果与业务完成分离，验收使用独立证据 | 记录并沿用既有行为与验收原则 |
| [0004](0004-small-console.md) | accepted | 控制台聚焦脚本运行，删除外围调试工作台 | 本轮用户授权精简，工作区已实现 |
| [0005](0005-repository-documentation.md) | accepted | 使用仓库内上下文与决策文档，移除 OpenSpec 目录并通过 Git 追溯 | 本轮用户明确确认 |
| [0006](0006-local-task-workspaces.md) | accepted | 框架主仓与外部本地任务工作区分离 | 本轮用户确认并授权实施 |

## 如何新增

只有出现需要保留理由的重要取舍时再新增；小修不要求写 ADR，也不要求每次修改更新所有文档。讨论尚未形成决定时，可直接写设计稿，不必先建 ADR。

状态使用 `proposed`（待讨论）、`accepted`（已采纳）、`superseded`（已被后续决策替代）。替代既有决策时保留原文和替代链接，不把过去的理由改写成从未存在。

简短模板如下，可按实际内容删减：

```markdown
# NNNN：决策标题

- 状态：proposed / accepted / superseded
- 日期：YYYY-MM-DD（说明记录或确认依据）

## 背景
要解决的具体问题和已知事实。

## 决定
已采纳或待讨论的选择；明确它的状态。

## 代价
接受的限制与没有选择的方向。

## 重审条件
什么新证据会使这项取舍值得调整。

## 依据
相关代码、现状和设计稿链接。
```
