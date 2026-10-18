# 0006：框架主仓与外部本地任务工作区分离

- 状态：accepted
- 日期：2026-10-18（用户确认并授权实施）
- 性质：数据根、仓库范围与分支约定

## 背景

通用执行框架与具体任务脚本、图像素材、玩法记录混在一个仓库中，会使任务调整影响框架主线，也容易误把游戏专用分支当成长期项目入口。

已有任务路由和子脚本调用实验尚未采纳，不能通过整理分支把草案功能合入稳定主线。当前需要的是清楚的数据归属和一致的本地运行入口。

## 决定

主仓保存通用框架、测试、开发验收靶场和少量通用示例；业务脚本、素材、状态配置、任务上下文及运行记录保存在仓库外的本地工作区，常用位置为 `~/StarWorkspaces/<name>`。任务资料不随主仓上传。

全局参数 `star --workspace PATH list/details/run/run-plan/ui` 选择任务根。该根包含 `scripts/*.json`、`assets/` 和其中的 `screen-states.json`；列表、依赖检查、运行与状态读取使用同一个根。

显式工作区只加载自身文件脚本，不混入内置或主仓示例。省略参数时保留仓库根的通用示例模式，供上手和开发验证使用。

一个 UI 服务绑定一个工作区，页面显示其路径；切换工作区通过启动相应服务完成，不增加项目选择器。工作区是任务数据选择边界，不是新的操作系统沙箱。

`main` 保持稳定，框架开发使用短生命周期的通用能力分支；业务任务不创建游戏专用分支。遗留未合并实验先保存本地 Git bundle 再清理分支，草案功能不因此进入主线；独有任务资料先迁出并核对。

局部恢复、任务路由与子脚本调用仍未采纳，见 [讨论稿](../design/local-recovery.md)。本决定只确立工作区边界，不改变当前步骤语义。

## 代价

- 框架与任务资料分别保存，迁移设备时需要单独备份本地工作区。
- 显式工作区不继承内置示例；需要示例时由 Agent 将必要文件复制到该工作区并维护。
- 一个控制台不能直接切换多个工作区；脚本修改仍按当前服务的加载生命周期生效。

## 重审条件

当真实使用反复出现多工作区切换、共享资源或备份困难时，再评估针对该困难的能力；不据目录数量预先建立多项目平台。

## 依据

- [CLI](../../src/game_automation/platform/local_desktop/entrypoints/cli.py)、[装配](../../src/game_automation/platform/local_desktop/composition.py)。
- [脚本发现](../../src/game_automation/portable/application/project_scripts.py)、[资源路径](../../src/game_automation/portable/application/project_assets.py)、[状态 reader](../../src/game_automation/portable/application/screen_state_reader.py)。
- [运行说明](../../README.md)、[当前状态](../current-state.md)。
