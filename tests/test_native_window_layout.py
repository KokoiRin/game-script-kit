"""验证运行和观察页面的窄窗口选择及纯几何布局。

本 module 只运行 Foundation 计算，不启动 Star、获取真实屏幕或改变其他窗口。
"""

import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != "darwin", reason="requires macOS Swift SDK")
def test_compact_pages_and_wide_restore_respect_visible_screen(tmp_path):
    """运行和观察采用窄版，准备页恢复宽版并约束屏幕边界。"""
    source = (
        Path(__file__).resolve().parents[1]
        / "native/StarDesktop/Sources/StarDesktop/WindowLayout.swift"
    )
    harness = tmp_path / "main.swift"
    harness.write_text("""import Foundation
import CoreGraphics
precondition(usesCompactLayout(for: "run"))
precondition(usesCompactLayout(for: "observe"))
precondition(!usesCompactLayout(for: "prepare"))
let screen = CGRect(x: 0, y: 33, width: 1440, height: 900)
let side = sidePanelFrame(in: screen)
precondition(side.size == CGSize(width: 520, height: 820))
precondition(side.maxX == screen.maxX && side.maxY == screen.maxY)
let external = CGRect(x: -1920, y: -100, width: 1920, height: 1080)
let externalSide = sidePanelFrame(in: external)
precondition(external.contains(externalSide))
precondition(externalSide.maxX == external.maxX && externalSide.maxY == external.maxY)
let small = CGRect(x: -300, y: 40, width: 300, height: 500)
precondition(sidePanelFrame(in: small) == small)
let original = CGRect(x: 10, y: 45, width: 1100, height: 850)
precondition(windowFrame(original, fitting: screen) == original)
let offscreen = CGRect(x: -500, y: -300, width: 1600, height: 1000)
precondition(windowFrame(offscreen, fitting: screen) == screen)
let consoleSize = CGSize(width: 520, height: 820)
let game = CGRect(x: 100, y: 40, width: 856, height: 674)
let attached = companionFrame(target: game, consoleSize: consoleSize, desktopTop: 1000)
precondition(attached.minX == game.maxX && attached.maxY == 960)
precondition(attached.size == consoleSize)
let beyondRight = CGRect(x: 1500, y: 40, width: 856, height: 674)
precondition(companionFrame(target: beyondRight, consoleSize: consoleSize, desktopTop: 1000).minX == 2356)
let upperLeft = CGRect(x: -1800, y: -900, width: 856, height: 674)
let upperAttached = companionFrame(target: upperLeft, consoleSize: consoleSize, desktopTop: 1000)
precondition(upperAttached.minX == -944 && upperAttached.maxY == 1900)
var visibility = CompanionVisibility()
precondition(!visibility.shouldReveal(targetIsFront: false, mouseDown: false, clickInsideTarget: false))
precondition(visibility.shouldReveal(targetIsFront: true, mouseDown: false, clickInsideTarget: false))
precondition(!visibility.shouldReveal(targetIsFront: true, mouseDown: false, clickInsideTarget: false))
precondition(visibility.shouldReveal(targetIsFront: true, mouseDown: true, clickInsideTarget: true))
precondition(!visibility.shouldReveal(targetIsFront: true, mouseDown: true, clickInsideTarget: true))
precondition(!visibility.shouldReveal(targetIsFront: false, mouseDown: false, clickInsideTarget: true))
precondition(!visibility.shouldReveal(targetIsFront: false, mouseDown: true, clickInsideTarget: true))
""")
    binary = tmp_path / "layout"
    subprocess.run(
        [
            "swiftc",
            "-module-cache-path",
            str(tmp_path / "cache"),
            str(source),
            str(harness),
            "-o",
            str(binary),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run([str(binary)], check=True)
