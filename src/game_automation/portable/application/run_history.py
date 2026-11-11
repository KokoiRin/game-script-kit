"""声明控制台持久运行记录的应用端口。

会话负责决定记录时机，存储 adapter 负责落盘和查询；本 module 不执行步骤，
不绑定数据库，也不把动作日志解释成业务成功。
"""

from typing import Protocol


class RunHistoryStore(Protocol):
    """提供逐次隔离、可持续追加的运行记录。"""

    def begin(self, name: str, dry_run: bool) -> str:
        """在任何输入前建立记录并返回唯一标识，失败时抛出 OSError。"""
        ...

    def append(self, run_id: str, kind: str, data: object) -> None:
        """提交一条带时间的记录，不等待整次运行结束。"""
        ...

    def finish(self, run_id: str, exit_code: int, finish_reason: str) -> None:
        """保存实际结束结果，不能把缺失结束记录视为完成。"""
        ...

    def list_runs(self) -> tuple[dict[str, object], ...]:
        """返回最近运行的摘要，顺序为从新到旧。"""
        ...

    def read_run(self, run_id: str) -> dict[str, object]:
        """读取一份摘要和完整记录，不存在时抛出 LookupError。"""
        ...
