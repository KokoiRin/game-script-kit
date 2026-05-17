"""实现 engine.ports.KeyStateReader — 从终端读取按键状态。"""

from __future__ import annotations

import os
import sys
from collections import deque
from typing import TextIO

from game_automation.engine.ports import KeyStateReader



class TerminalKeyStateReader(KeyStateReader):
    def __init__(self, stream: TextIO | None = None) -> None:
        """初始化终端按键读取 adapter，并在 POSIX 终端启用 cbreak 模式。"""
        self._stream = stream if stream is not None else sys.stdin
        self._buffer: deque[str] = deque()
        self._fd: int | None = None
        self._old_termios: list[object] | None = None

        if os.name != "nt":
            self._enable_posix_cbreak()

    def is_pressed(self, key: str) -> bool:
        """检查指定按键是否在本轮检测中被触发。"""
        self._drain_available_keys()
        try:
            self._buffer.remove(key)
        except ValueError:
            return False
        return True

    def close(self) -> None:
        """恢复终端输入模式。"""
        if self._fd is None or self._old_termios is None:
            return
        try:
            import termios

            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old_termios)
        finally:
            self._fd = None
            self._old_termios = None

    def _enable_posix_cbreak(self) -> None:
        """在 POSIX 终端中启用单字符读取。"""
        if not self._stream.isatty():
            raise RuntimeError("coordinate recorder requires an interactive terminal")
        try:
            import termios
            import tty

            self._fd = self._stream.fileno()
            self._old_termios = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)
        except Exception as exc:
            raise RuntimeError(
                "failed to configure terminal keyboard input"
            ) from exc

    def _drain_available_keys(self) -> None:
        """读取当前终端中已经可用的按键事件。"""
        if os.name == "nt":
            self._drain_windows_keys()
            return
        self._drain_posix_keys()

    def _drain_posix_keys(self) -> None:
        """读取 POSIX 终端中已经可用的字符。"""
        if self._fd is None:
            raise RuntimeError("terminal keyboard input is not configured")
        try:
            import select

            while select.select([self._fd], [], [], 0)[0]:
                self._buffer.append(self._stream.read(1))
        except Exception as exc:
            raise RuntimeError("failed to read terminal keyboard input") from exc

    def _drain_windows_keys(self) -> None:
        """读取 Windows 控制台中已经可用的字符。"""
        try:
            import msvcrt

            while msvcrt.kbhit():
                self._buffer.append(msvcrt.getwch())
        except Exception as exc:
            raise RuntimeError("failed to read terminal keyboard input") from exc
