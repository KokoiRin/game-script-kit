"""保存桌面运行的日志、条目结果与中断画面。

本模块拥有工作区诊断文件和存储故障；消费执行器冻结的证据，不访问窗口。
"""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


class RunArchive:
    """为一次运行建立独立记录，并隔离全部文件系统故障。"""

    def __init__(self, workspace: Path, entries, *, dry_run: bool):
        """创建运行目录并记录启动状态与编排快照。"""
        now = datetime.now(UTC)
        self.warnings: tuple[str, ...] = ()
        self.path = (
            workspace
            / ".star"
            / "runs"
            / (now.strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8])
        )
        self.data = {
            "started_at": now.isoformat(),
            "workspace": str(workspace),
            "dry_run": dry_run,
            "finish_reason": "running",
            "phase": "preparing",
            "items": [
                {"index": index, **asdict(entry), "finish_reason": "pending"}
                for index, entry in enumerate(entries, 1)
            ],
        }
        try:
            self.path.mkdir(parents=True)
        except OSError as exc:
            self._warn("运行记录目录创建失败", exc)
            self.path = None
        self.write("stdout", "")
        self.write("stderr", "")
        self._save_summary()

    def _warn(self, operation: str, error: OSError) -> None:
        """保留有界且去重的存储警告供控制台展示。"""
        message = f"{operation} {error}"
        if message not in self.warnings:
            self.warnings = (*self.warnings, message)[-8:]

    def write(self, channel: str, text: str) -> None:
        """完整追加文本，界面截断不会影响磁盘记录。"""
        if self.path is None:
            return
        try:
            with (self.path / f"{channel}.log").open("a", encoding="utf-8") as stream:
                stream.write(text)
        except OSError as exc:
            self._warn("运行日志保存失败", exc)

    def start_item(self, index: int) -> None:
        """记录当前条目及开始时间，重复任务按序号分别保存。"""
        self.data.update(phase="running", current_item=index)
        self.data["items"][index - 1].update(
            started_at=datetime.now(UTC).isoformat(), finish_reason="running"
        )
        self._save_summary()

    def wait_after(self) -> None:
        """记录任务会话关闭后的等待阶段。"""
        self.data["phase"] = "waiting"
        self._save_summary()

    def finish_item(self, index: int, result) -> None:
        """保存最终结果及已冻结的 PNG，不再读取已关闭的窗口源。"""
        item = self.data["items"][index - 1]
        item.update(
            exit_code=result.exit_code,
            error_message=result.error_message,
            finish_reason=result.finish_reason,
            finished_at=datetime.now(UTC).isoformat(),
        )
        diagnostic = result.diagnostic
        if diagnostic is not None:
            item["traceback"] = diagnostic.traceback
            if diagnostic.window is not None:
                item["window"] = asdict(diagnostic.window)
            if diagnostic.capture_error:
                item["screenshot_error"] = diagnostic.capture_error
            if diagnostic.png is not None and self.path is not None:
                name = f"interrupted-{index:03d}.png"
                try:
                    (self.path / name).write_bytes(diagnostic.png)
                    item["screenshot"] = name
                    item["screenshot_saved_at"] = datetime.now(UTC).isoformat()
                except OSError as exc:
                    item["screenshot_error"] = str(exc)
                    self._warn("中断截图保存失败", exc)
        self._save_summary()

    def finish(self, exit_code: int, finish_reason: str) -> None:
        """写入最终状态，窗口尚未打开或已关闭时明确说明缺图原因。"""
        if (
            finish_reason not in {"completed", "skipped"}
            and self.data["phase"] != "running"
        ):
            self.data["screenshot_error"] = (
                "任务间等待时已关闭窗口会话"
                if self.data["phase"] == "waiting"
                else "任务初始化阶段尚未取得目标窗口"
            )
        self.data.update(
            exit_code=exit_code,
            finish_reason=finish_reason,
            finished_at=datetime.now(UTC).isoformat(),
        )
        self._save_summary()

    def _save_summary(self) -> None:
        """原子替换摘要，存储失败保留内存状态及可见警告。"""
        if self.path is None:
            return
        try:
            temporary = self.path / "summary.tmp"
            temporary.write_text(
                json.dumps(
                    {**self.data, "warnings": self.warnings},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(self.path / "summary.json")
        except OSError as exc:
            self._warn("运行摘要保存失败", exc)
