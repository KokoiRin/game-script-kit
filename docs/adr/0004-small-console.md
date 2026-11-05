# 0004：控制台聚焦脚本运行

- 状态：accepted
- 日期：2026-10-18（本轮用户授权精简，当前工作区已实现）
- 性质：产品范围与本地控制边界
- 后续修订：2026-11-05 的 [ADR 0007](0007-preparation-and-execution.md) 新增独立素材准备壳；本记录仍约束原运行控制台，删除旧调试路由的历史不变。
- 界面替换：同日 [ADR 0008](0008-native-macos-desktop.md) 以原生壳组合准备与运行，旧 HTTP UI 已删除；本记录中的 HTTP 描述是历史取舍。

## 背景

精简前的控制台同时提供脚本运行、图片浏览与独立点击、截图诊断、区域框选、匹配预览、裁剪导出、连续状态探测和运行测试。

这些外围工具扩大了维护面和使用负担，而真实任务尚未闭环。用户明确要求大幅削减无用调试功能，使项目重新聚焦实际任务。

## 决定

控制台保留脚本列表与详情、模拟或真实运行、停止、运行记录和结束原因。CLI 继续提供脚本运行、Run Plan 与坐标记录；具体用法见 [README](../../README.md)。

后续采纳的 [ADR 0006](0006-local-task-workspaces.md) 将一个服务绑定到一个显式任务工作区，页面显示路径；这不引入多项目管理界面。

删除 UI/HTTP 中的运行 pytest、独立图片点击与资源浏览、截图及区域诊断工具、匹配预览、裁剪导出，以及连续状态探测和候选统计展示。CLI 的相应诊断命令同步删除，详见 [当前状态](../current-state.md)。

保留识图、条件等待和核心状态读取，因为脚本执行仍依赖这些能力。`ProjectScreenStateReader` 直接通过注入的图像 ports 按需读取，不再从 UI 后台探测会话缓存取得状态。

视觉靶场仅作为开发验收工具保留。今后若需重建某项诊断能力，以真实任务反复遇到的具体困难为依据，优先解决一个明确环节，不恢复整套调试工作台。

## 代价

- 图片和区域准备的便利程度降低，当前使用已有素材、系统工具与配置文件。
- 已删除的调试路由和命令不再兼容；调用方需停止使用这些入口。
- 精简控制台没有解决任务创建、局部恢复和目标窗口接入的全部问题，差距仍需如实保留。

## 重审条件

当真实任务证明确有高频配置或排障环节，且现有工具成本明显高于新增小能力的维护成本时，重审该项工具；不以调试数据可展示为理由扩展控制台。

## 依据

- 历史 HTTP 入口 `src/game_automation/platform/local_desktop/entrypoints/local_ui.py` 和 `ui_static/` 已删除，可从原主线 `4c51f3b` 查询。
- [本地控制用例](../../src/game_automation/portable/application/local_control.py)、[状态 reader](../../src/game_automation/portable/application/screen_state_reader.py)。
- [CLI](../../src/game_automation/platform/local_desktop/entrypoints/cli.py)、[重启计划](../restart-plan.md)。
