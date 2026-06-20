# Design: add-script-details-cli

## Boundary

`star details` 只做入口层职责：解析脚本名、查找脚本、装配共享资源、调用 application presenter、打印结果。步骤摘要、依赖收集和 readiness 判断继续由 `describe_script_details` 完成。

## Output

输出采用稳定的文本分组：

- `脚本`
- `步骤`
- `依赖`
- `图片依赖`
- `依赖检查`

这样用户可以直接从 CLI 看到 dry-run 需要的图片路径，也能看到搜索别名缺失或图片文件缺失。

## Error Handling

未知脚本返回退出码 `1`。共享资源配置非法或脚本详情生成失败返回非零退出码，并把错误写入 stderr。
