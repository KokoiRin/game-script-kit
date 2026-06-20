## 1. 规格与测试

- [x] 1.1 补充 `screen-state-probe` 规格，定义 CLI 区域裁剪导出行为。
- [x] 1.2 添加 application 行为测试，覆盖命名区域裁剪成功路径。
- [x] 1.3 添加 CLI 行为测试，覆盖区域裁剪命令成功和失败输出。

## 2. 实现

- [x] 2.1 新增 application 区域裁剪用例。
- [x] 2.2 复用现有状态配置校验、截图能力和区域坐标换算。
- [x] 2.3 新增 `star capture-region-crops` 子命令。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 归档 OpenSpec change。
