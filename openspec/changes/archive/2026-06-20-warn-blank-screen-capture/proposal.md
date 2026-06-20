## Why

真实 smoke 显示本机截图 adapter 可以成功保存文件，但文件内容可能是纯黑图。此时状态识别和裁剪导出都会继续运行，用户只能看到“保存成功”，很难判断是素材区域错误还是截图权限/会话不可用。

## What Changes

- 截图诊断类 application 用例在保存截图后检查图像是否疑似全黑。
- 疑似全黑时，命令仍保留已保存文件，但在用户可见输出中提示检查屏幕录制权限、前台窗口或运行会话。
- 该提示由 application 层生成，CLI/UI 继续只负责展示结果。

## Capabilities

### New Capabilities

### Modified Capabilities

- `screen-state-probe`: 截图诊断入口增加“疑似全黑截图”的用户可见警告。

## Impact

- 影响 application 层截图诊断用例、CLI/UI 展示链路的测试，以及 `screen-state-probe` 规格。
- 不改变截图 adapter、图像匹配算法、状态选择规则、脚本语义或截图文件保存路径。
