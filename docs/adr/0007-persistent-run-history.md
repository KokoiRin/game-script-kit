# 0007：按工作区持久保存控制台运行记录

- 状态：accepted
- 日期：2026-10-21（用户要求查明此前中断，并授权补齐日志保存）
- 性质：运行会话记录、存储端口与查询入口

## 背景

控制台原本只在内存中保留最后一次后台会话。再次运行会替换它，服务重启会丢失全部记录，无法逐次解释此前中断。执行器已有步骤、识图、取消与结束事件，可以直接保存，无须新增脚本规则或桌面诊断工具。

## 决定

控制台后台会话在输入动作前建立独立记录，逐条保存带时区的记录时间、stdout/stderr、步骤事件及停止请求，并原样保存实际结束原因和退出码。没有终态的记录使用 `unfinished`；它表示尚无结束记录，不能推定服务退出、取消或成功。活动状态只能由持有当前会话的应用确认。

应用层拥有记录时机，并消费 `RunHistoryStore` 端口；SQLite adapter 保存所选工作区内的 `.star/runs.sqlite3`，由平台装配注入。入口不解释步骤或推断结束原因。SQLite 每次追加独立事务，运行摘要与日志正文分开查询；只查最近 50 份摘要，按 ID 仍能导出全部记录。

开始前存储不可用时返回明确错误，不接触桌面。开始后写入失败不改变已发生动作或实际运行结果，保留内存输出与取消能力并提示记录缺失；持久记录保留尚无结束记录，避免制造完整记录的假象。读历史失败明确展示错误，不静默当成没有记录。

控制台提供历史选择、摘要、最后 300 行预览及完整 JSON 下载；CLI `history [RUN_ID] [--json]` 查询同一存储。此轮保存范围为控制台后台会话，CLI `run` / `run-plan` 不因此改写日志策略。

可以抢救仍存活的旧服务快照；没有原始时间戳的旧记录保留空时间并注明来源，不能把导入时间写成实际运行时间。日志不主动采集剪贴板内容或截图，不作为业务完成证据。

## 代价

记录随工作区分别备份，持续循环的完整日志会占用磁盘；本轮不自动清理历史。每条事务写入有本地 I/O 开销。异常退出只能保证此前已提交的记录可查询，不能保证得到终态或解释当时所有画面变化。

## 重审条件

真实使用发现磁盘增长、追加耗时或 CLI 运行追溯成为具体困难时，再评估保留策略、批量提交或扩展保存入口。

## 依据

- [应用端口](../../src/game_automation/portable/application/run_history.py)、[后台会话](../../src/game_automation/portable/application/local_control.py)。
- [SQLite adapter](../../src/game_automation/portable/adapters/sqlite_run_history.py)、[平台装配](../../src/game_automation/platform/local_desktop/composition.py)。
- [HTTP](../../src/game_automation/platform/local_desktop/entrypoints/local_ui.py)、[CLI](../../src/game_automation/platform/local_desktop/entrypoints/cli.py)。
- [运行记录测试](../../tests/test_run_history.py)、[HTTP 测试](../../tests/test_local_control_ui.py)。
