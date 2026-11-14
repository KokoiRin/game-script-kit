"""演示等待后发送粘贴组合键，按键生命周期由任务上下文管理。"""

TASK = {"name": "粘贴"}


def run(ctx):
    """等待三秒后发送一次 Command+V。"""
    ctx.wait(3)
    ctx.hotkey("command", "v")
