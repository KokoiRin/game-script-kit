## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 规格，定义探测候选裁剪导出行为。
- [x] 1.2 添加 application 测试，覆盖候选裁剪导出、无候选和错误路径。
- [x] 1.3 添加 CLI 测试，覆盖 `capture-probe-crops` 输出和参数传递。

## 2. 实现

- [x] 2.1 在 application 层新增探测候选裁剪用例和输出目录。
- [x] 2.2 复用探测结果和截图坐标换算保存候选裁剪图。
- [x] 2.3 新增 CLI 子命令 `capture-probe-crops`。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 `capture-probe-crops` smoke。
- [x] 3.3 归档 OpenSpec change。
