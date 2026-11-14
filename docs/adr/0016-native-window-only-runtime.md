# 0016 只保留 Python 任务与原生窗口运行

- 状态为 accepted
- 日期为 2026-11-14，用户确认继续用 Python 文件编写任务，并要求去掉残留的脚本概念和双套坐标/状态系统

## 背景

[ADR 0015](0015-python-only-tasks.md) 已把作者格式收成 `TASK` 与同步 `run(ctx)`。[ADR 0012](0012-native-script-runtime.md) 引入显式 macOS 窗口会话时，仍保留默认 `desktop` 后端、屏幕绝对坐标和 `assets/screen-states.json`。两条真实运行路径并存，模块名也继续沿用脚本时期的 `script_*`。

## 决定

真实运行只接受 `target.backend` 为 `macos-window` 或 `macos-window-background` 的任务。坐标相对该窗口，状态、共享搜索和观察规则只读取 `assets/window-states.json`。缺少该目标时真实运行直接失败，不再激活应用、不再按屏幕矩形绑定窗口，也不再使用全局指针或整屏识图。

dry-run 仍可不打开窗口、不接触桌面，用固定颜色、图片和状态替身执行 Python 流程。未绑定窗口只按作者写下的窗口相对坐标原样传递，不构成第二套屏幕坐标。

任务目录、详情、依赖和运行用例使用 task 命名。`scripts/` 仍是工作区里的 Python 文件目录。Swift 与 Python 之间的 `script.*` 协议字段保持不变。JSON 只继续用于窗口规则和素材配置，不再作为任务格式被发现或提示迁移。

## 代价

没有原生窗口声明的任务不能真实运行。外部工作区里仍写 `desktop` 或依赖 `screen-states.json` 的任务需要改为原生目标和窗口规则；本轮不修改仓库外工作区。历史 ADR 保留当时的双路径理由，不以本文回改原文。

## 重审条件

出现第二种已验收的真实运行时，再单独决定它的坐标和状态文件，而不是恢复隐式桌面回退。

## 依据

作者接口见 [函数任务说明](../task-functions.md)，当前行为见 [当前实现](../current-state.md)。
