## 1. 测试

- [x] 1.1 添加 application 测试，覆盖普通截图疑似全黑时返回警告。
- [x] 1.2 添加 application 测试，覆盖非全黑截图不返回警告。
- [x] 1.3 添加诊断/裁剪用例测试，覆盖复用原始截图健康检查。

## 2. 实现

- [x] 2.1 在 application 层新增截图疑似全黑检测 helper。
- [x] 2.2 让 `capture-screen`、区域诊断、探测诊断、区域裁剪和候选裁剪复用该警告。
- [x] 2.3 保持 CLI/UI 入口只展示 application 返回结果，不新增入口层图片判断。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 运行真实 `capture-screen` smoke，确认当前黑屏环境会输出警告。
- [x] 3.3 归档 OpenSpec change。
