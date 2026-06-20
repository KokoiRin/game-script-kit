## 1. HTTP adapter

- [x] 1.1 添加 UI HTTP 测试，覆盖 `/api/diagnose-screen` 委托 application 并返回截图预览 URL。
- [x] 1.2 添加 UI HTTP 测试，覆盖非法最低置信度不会调用 application。
- [x] 1.3 在本地 UI HTTP adapter 中实现 `/api/diagnose-screen`。

## 2. Frontend

- [x] 2.1 添加页面/静态资源测试，覆盖环境诊断按钮和前端请求。
- [x] 2.2 在 HTML/JS 中增加环境诊断按钮并复用现有结果日志和截图预览。

## 3. 验证和归档

- [x] 3.1 运行相关 pytest、全量 pytest、OpenSpec 校验和 diff 检查。
- [x] 3.2 完成 OpenSpec 归档。
- [x] 3.3 提交并推送当前分支。
