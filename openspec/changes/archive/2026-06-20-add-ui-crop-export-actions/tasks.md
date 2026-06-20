## 1. 测试

- [x] 1.1 添加 UI 静态资源测试，覆盖两个裁剪导出按钮和 fetch 调用。
- [x] 1.2 添加 HTTP adapter 测试，覆盖区域裁剪接口委托 application。
- [x] 1.3 添加 HTTP adapter 测试，覆盖候选裁剪接口传递最低置信度并展示错误。

## 2. 实现

- [x] 2.1 在本地 UI HTML 中新增区域裁剪和候选裁剪按钮。
- [x] 2.2 在本地 UI JS 中新增按钮绑定和 fetch 调用。
- [x] 2.3 在 HTTP adapter 中新增 `/api/capture-region-crops` 和 `/api/capture-probe-crops`。

## 3. 验证与归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 启动本地 UI smoke，确认页面和接口可用。
- [x] 3.3 归档 OpenSpec change。
