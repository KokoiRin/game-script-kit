## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 规格，定义 CLI 截图诊断命令。
- [x] 1.2 添加 CLI 行为测试，覆盖全屏截图诊断成功和失败输出。
- [x] 1.3 添加 CLI 行为测试，覆盖区域诊断成功和失败输出。

## 2. 实现

- [x] 2.1 为 `star` 增加 `capture-screen` 子命令。
- [x] 2.2 为 `star` 增加 `capture-region-diagnostics` 子命令。
- [x] 2.3 复用 application 层 `ControlResult` 输出映射，保持 CLI 入口薄。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
