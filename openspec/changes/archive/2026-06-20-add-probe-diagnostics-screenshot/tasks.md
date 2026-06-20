## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 和 `local-control-ui` 规格，定义探测诊断截图行为。
- [x] 1.2 添加 application 测试，覆盖探测诊断截图绘制候选最佳位置和错误路径。
- [x] 1.3 添加 CLI 测试，覆盖 `capture-probe-diagnostics` 输出和参数传递。
- [x] 1.4 添加 UI HTTP/静态资源测试，覆盖探测诊断按钮和 endpoint。

## 2. 实现

- [x] 2.1 在 application 层新增探测诊断截图用例和输出路径。
- [x] 2.2 复用现有区域绘制能力，增加候选最佳位置绘制。
- [x] 2.3 新增 CLI 子命令 `capture-probe-diagnostics`。
- [x] 2.4 新增 UI HTTP endpoint、按钮和前端调用。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 `capture-probe-diagnostics` smoke。
- [x] 3.3 归档 OpenSpec change。
