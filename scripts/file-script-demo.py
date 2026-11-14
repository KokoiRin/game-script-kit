"""演示文件任务声明和命名点位，运行时用 Python 选择状态分支。"""

TASK = {
    "name": "file-script-demo",
    "resources": {"points": {"示例按钮": {"x": 100, "y": 200}}},
    "requires": {"states": ["主页"]},
}


def run(ctx):
    """主页状态下点击声明的示例按钮。"""
    if ctx.state() == "主页":
        ctx.click("示例按钮")
