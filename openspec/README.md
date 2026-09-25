# OpenSpec 历史资料

自 2026-09-08 起，OpenSpec 退出本项目默认开发流程。本目录原有文件原地保留，用于追溯需求、验收场景和设计取舍。

- `specs/`：停止维护时的 17 份行为规格快照，不作为持续同步的当前规格。
- `changes/archive/`：81 个已归档 change 的提案、设计、任务清单和 delta；目录没有待完成的活动 change。
- `config.yaml`：保留旧工具配置，以便必要时查看历史资料；不要求新开发安装或运行 OpenSpec。

新需求直接明确行为和范围，用测试保护实现；重要设计按需写入 `docs/`。新工作不新增 change、不回写历史任务清单、不要求 OpenSpec 校验。

开发规则见 [AGENTS.md](../AGENTS.md)，稳定架构约束见 [docs/architecture.md](../docs/architecture.md)，使用方法见 [README.md](../README.md)。`tests/` 中的自动化测试以及 `tools/` 中的验证工具继续保留和维护。

历史规格可能包含旧目录、过时接口或已改变的行为。复用历史场景时，先核对当前用户需求、代码和测试；发现差异应明确说明，不能直接将旧描述视为实现完成的证据。
