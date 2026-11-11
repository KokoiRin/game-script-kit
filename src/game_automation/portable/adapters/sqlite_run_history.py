"""把应用运行记录保存到工作区内的 SQLite 数据库。

实现 RunHistoryStore 的事务追加和查询，不执行脚本、不探测桌面。每次写入独立
提交，服务退出前已提交的记录仍可读取；没有结束记录时保留 unfinished。
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from uuid import uuid4


def _now() -> str:
    """返回带时区的 UTC 时间供入口按本地时区展示。"""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class SqliteRunHistoryStore:
    """使用短事务保存每次运行及其有序日志。"""

    def __init__(self, path: Path) -> None:
        """保存数据库位置，单纯构造和空历史查询不创建文件。"""
        self.path = path.resolve()

    @contextmanager
    def _connection(self, *, create: bool = False):
        """打开独立连接并将存储故障归一为端口约定的 OSError。"""
        connection = None
        try:
            if create:
                self.path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.path.as_uri() + ("?mode=rwc" if create else "?mode=rw"), uri=True)
            connection.row_factory = sqlite3.Row
            with connection:
                if create:
                    connection.executescript("""
                        CREATE TABLE IF NOT EXISTS runs (
                            id TEXT PRIMARY KEY, name TEXT NOT NULL, dry_run INTEGER NOT NULL,
                            created_at TEXT NOT NULL, started_at TEXT, ended_at TEXT,
                            finish_reason TEXT NOT NULL, exit_code INTEGER,
                            last_step TEXT NOT NULL DEFAULT '', error TEXT NOT NULL DEFAULT '',
                            source TEXT NOT NULL DEFAULT 'console'
                        );
                        CREATE TABLE IF NOT EXISTS records (
                            sequence INTEGER PRIMARY KEY, run_id TEXT NOT NULL,
                            recorded_at TEXT, kind TEXT NOT NULL, data TEXT NOT NULL
                        );
                        CREATE INDEX IF NOT EXISTS records_by_run ON records(run_id, sequence);
                    """)
                yield connection
        except sqlite3.Error as exc:
            raise OSError(f"运行日志存储失败：{exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    def begin(self, name: str, dry_run: bool) -> str:
        """先提交运行身份，异常退出时也能看见尚无结束记录的尝试。"""
        run_id, now = uuid4().hex, _now()
        with self._connection(create=True) as connection:
            connection.execute(
                "INSERT INTO runs(id, name, dry_run, created_at, started_at, finish_reason) VALUES(?, ?, ?, ?, ?, ?)",
                (run_id, name, dry_run, now, now, "unfinished"),
            )
        return run_id

    def append(self, run_id: str, kind: str, data: object) -> None:
        """在单个事务中追加日志并更新最后步骤或错误摘要。"""
        with self._connection() as connection:
            connection.execute(
                "INSERT INTO records(run_id, recorded_at, kind, data) VALUES(?, ?, ?, ?)",
                (run_id, _now(), kind, json.dumps(data, ensure_ascii=False)),
            )
            if kind == "event" and data.get("type") == "step_started":
                step = f"{data['path']} {data['step']}: {data['details'].get('summary', '')}"
                connection.execute("UPDATE runs SET last_step=? WHERE id=?", (step, run_id))
            elif kind == "stderr":
                connection.execute("UPDATE runs SET error=error || ? WHERE id=?", (str(data), run_id))

    def finish(self, run_id: str, exit_code: int, finish_reason: str) -> None:
        """原样提交终态，保留取消、条件停止和失败之间的区别。"""
        with self._connection() as connection:
            connection.execute(
                "UPDATE runs SET ended_at=?, exit_code=?, finish_reason=? WHERE id=?",
                (_now(), exit_code, finish_reason, run_id),
            )

    def list_runs(self) -> tuple[dict[str, object], ...]:
        """只查最近五十份摘要，避免重复扫描历史日志正文。"""
        if not self.path.exists():
            return ()
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM runs ORDER BY rowid DESC LIMIT 50").fetchall()
        return tuple(self._summary(row) for row in rows)

    def read_run(self, run_id: str) -> dict[str, object]:
        """按参数化标识查询记录，拒绝把用户输入当文件路径。"""
        if not self.path.exists():
            raise LookupError("运行记录不存在")
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise LookupError("运行记录不存在")
            records = connection.execute(
                "SELECT recorded_at, kind, data FROM records WHERE run_id=? ORDER BY sequence", (run_id,),
            ).fetchall()
        return {
            "summary": self._summary(row),
            "records": [{"recorded_at": r["recorded_at"], "kind": r["kind"], "data": json.loads(r["data"])} for r in records],
        }

    def import_snapshot(self, name: str, dry_run: bool, snapshot: dict[str, object]) -> str:
        """抢救旧服务快照，原时间未知时留空，避免伪造运行时间。"""
        run_id = self.begin(name, dry_run)
        with self._connection() as connection:
            connection.execute(
                "UPDATE runs SET source='recovered', started_at=NULL, ended_at=NULL, finish_reason=?, exit_code=?, error=? WHERE id=?",
                (snapshot["finish_reason"], snapshot["exit_code"], snapshot["stderr"], run_id),
            )
            entries = [("stdout", snapshot["stdout"]), ("stderr", snapshot["stderr"])]
            entries.extend(("event", event) for event in snapshot.get("events", ()))
            connection.executemany(
                "INSERT INTO records(run_id, recorded_at, kind, data) VALUES(?, NULL, ?, ?)",
                [(run_id, kind, json.dumps(data, ensure_ascii=False)) for kind, data in entries],
            )
            last_step = next((e for e in reversed(snapshot.get("events", ())) if e["type"] == "step_started"), None)
            if last_step:
                connection.execute("UPDATE runs SET last_step=? WHERE id=?", (
                    f"{last_step['path']} {last_step['step']}: {last_step['details'].get('summary', '')}", run_id,
                ))
        return run_id

    @staticmethod
    def _summary(row) -> dict[str, object]:
        """把数据库行转换为应用端口的独立摘要。"""
        result = dict(row)
        result["dry_run"] = bool(result["dry_run"])
        return result
