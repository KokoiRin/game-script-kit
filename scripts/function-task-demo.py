"""演示用普通 Python 函数组合任务，动作统一通过 Star 上下文执行。

先以 dry-run 运行。真实执行会点击声明的示例点位，需要自行准备目标窗口。
"""

TASK = {
    "name": "function-task-demo",
    "resources": {"points": {"示例点位": {"x": 120, "y": 180}}},
}


def click_once(ctx):
    """执行一次点击及可取消等待。"""
    ctx.click("示例点位")
    ctx.wait(0.1)


def run(ctx):
    """用函数与有限循环完成示例。"""
    with ctx.deadline(10):
        for index in range(4):
            if index == 1:
                continue
            click_once(ctx)
