# 窗口采集性能探索

日期：2026-11-06。本文件保留先前探索对照；随后用户授权以2到5Hz接入窗口流，当前实现见[ADR 0010](../adr/0010-window-stream-observation.md)。下表15Hz不是应用当前配置。

## 问题与范围

现有观察每轮核对窗口、启动系统截图命令、编码PNG落盘，再读回RGB识别。截图阶段显著大于当前少量ROI模板匹配，值得独立优化。

本轮只比较明确窗口的采集，复用外部任务工作区的尺寸、模板和ROI；不改runner、准备会话、素材、权限或已安装应用默认。具体窗口画面和实测原始数据保存在对应外部任务工作区，框架只维护通用实验工具。

## 实测

本机固定逻辑窗口856×674、RGB1712×1348、两条素材、每秒5次读取。停止旧观察后，5轮轮换6个方法，每case8次，共240次。每case首样本分开，热态每方法35个样本。全部读取成功且均识别出预期状态，零采集、回调与停流错误。仅代表本机本次负载；未测容量上限。

| 方法 | 采集/读缓存转RGB p95 | 加匹配 p95 | WindowServer源事件年龄 p95 |
| --- | ---: | ---: | ---: |
| 命令截图＋PNG | 284.7ms | 292.6ms | 无证明 |
| 旧Quartz直接CGImage | 56.5ms | 61.1ms | 无证明 |
| SCScreenshotManager单张sampleBuffer | 88.0ms | 92.1ms | 缺displayTime |
| SCStream 5Hz | 8.6ms | 13.3ms | 213.1ms |
| SCStream 10Hz | 14.0ms | 24.6ms | 114.9ms |
| SCStream 15Hz | 13.7ms | 24.9ms | 81.7ms |

旧截图命令与PNG读取转RGB热态中位分别205.0ms、29.7ms，窗口核对约1ms每次。15Hz流启动到首个完整帧中位83.7ms；启动单列。5Hz流40次读中8次重复，10/15Hz没有；流displayTime全部有效，当前contentRect/contentScale/scaleFactor与原始逻辑矩形、2倍像素比例一致。

10Hz流额外250次读取零错误，真实界面A→B→A的识别序列正确；15Hz额外175次零错误支持A→B，源年龄p95=78.5ms，后者没有在采集期间记录返回A。缺动作真值时间，不能据此声称切换延迟或完整UI确认延迟。实验后恢复旧2Hz观察，20轮成功、零失败，权限仍可用。

早期探针和第一组对照跨界面且有用户交互干扰，原始数据保留但不作为上表依据。早期SCK单张使用captureImage，正式工具采用captureSampleBuffer，两种接口的数字不能混用。锁屏期间的idle-only结果也不作为采集接口失败或游戏后台限制的证明。

## 复现

在Star checkout根目录运行，路径和窗口编号换成实际值。先手动停止原生观察，核对窗口身份、原始逻辑尺寸与像素尺寸。工具不会请求权限、发送输入、捕获音频或修改assets；macOS14+原生接口仅为本轮实验范围，未证明覆盖项目全部最低系统版本。

```sh
PYTHONPATH=src .venv/bin/python tools/benchmark_window_capture.py \
  --source-root /path/to/star-checkout \
  --workspace /path/to/task-workspace --window-id WINDOW_ID \
  --rounds 5 --samples 8 \
  --output /private/tmp/window-capture-comparison.json
```

先用 `--rounds 1 --samples 2` 检查本机metadata，再完整运行。`--methods baseline,sck_shot,stream_15` 可限制候选；完整默认还包括旧Quartz和5/10Hz流。可选 `--evidence-dir` 保存每case首图；性能主对照不保存PNG，避免引入额外编码成本。

## 指标与限制

- 请求式capture_rgb为请求到RGB完成；流的同名项为缓存读取转换。不能直接相除给捕获加速比。所有候选复用同一批量匹配逻辑。
- display_age为SDK mach absolute displayTime经CoreMedia换算，到读取完成的事件年龄。缺失、无效、未来时间单独计数；PTS仅作时间域诊断。不得把它写成游戏输入到绘制或UI确认的完整延迟。
- 读成功不等于新源帧成功；重复序号不计新帧，也不能连续确认。complete不自动证明像素变化，工具另报hash和实际源事件数。
- `performance_eligible`只表示没有记录错误，不表示满足新鲜度目标。探索门槛为读转RGB p95<50ms、有效源事件年龄p95<100ms；当前只有15Hz流同时达到。
- case CPU包含父进程、子进程、匹配、hash及可选图片保存，排除WindowServer/GPU。上表主组CPU中位：旧截图58.7%、单张SCK8.1%、15Hz流12.5%单核；不作整机功耗或长驻CPU承诺。RSS为进程生命周期峰值，不是每case独立分配。
- 所有方法核对原窗口ID/PID/标题、逻辑尺寸和输出像素。流额外检查contentRect/contentScale/scaleFactor，未知表示明确失败，不静默缩放素材。当前实测只验证未改尺寸的配置。
- 停流未确认会中止后续case，防止残留流污染测量。实验主运行循环不是生产工作线程；停止完成回调也不代替生产回调屏障验收。

## 建议与接入前条件

长期观察优先进入15Hz常驻单窗流接入原型，识别保持2或5Hz、所有素材共用同一帧。原生单张SCK本次已在5Hz的200ms预算内，适合准备页临时截图或结构更简单的初接入方案。旧Quartz API在本机SDK已废弃，只作对照，不选择长期默认。

生产接入必须让会话消费源时间与源序号，不能沿用read开始时间给缓存续期。先验证后台线程/运行循环、静态idle的新鲜度、关窗/最小化/锁屏/resize、停止与初始化竞态、迟到回调、长时间运行及重复启停回收，再决定默认源。当前应用保留旧采集方式，未更新已采纳ADR。

## 验证与证据

工具26项fake测试及项目完整621项测试通过（45.55s），差异空白检查通过；模拟与上面的真实桌面证据分开报告。统计和实现由同宿主模型的独立执行者复核，不能称为跨模型审查。

本次外部证据目录：`~/StarWorkspaces/mhxy/evidence/2026-11-06-capture-exploration/`，入口 `report.md`；主数据 `capture-comparison-controlled.json`，可重算 `summary.json`、`summarize_results.py`，状态数据与审查、测试记录同目录。业务图像留在该工作区。

依据：[Apple窗口采集示例](https://developer.apple.com/documentation/screencapturekit/capturing-screen-content-in-macos)、[帧元数据与队列说明](https://developer.apple.com/videos/play/wwdc2022/10155/)和本机SDK `SCStream.h`、`SCScreenshotManager.h`、`CGWindow.h`。

## 后续接入

用户明确无需15Hz。观察已按所选1/2/5Hz同步采集，默认2Hz，移除每轮命令与PNG往返。源时间及序号交给会话，原始系统时间先去重，停止使用系统完成与回调屏障；已验证真实工作线程、2/5Hz及重复启停。静态、锁屏恢复、真实强制回收与小时级验证仍未覆盖，最新实机与自动化结果见current-state，不用本探索的100ms门槛否定用户选择的低频预算。
