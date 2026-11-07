"""验证并排观察窗口的纯几何布局。

本 module 只运行 Foundation 计算，不启动 Star、获取真实屏幕或改变其他窗口。
"""

from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='requires macOS Swift SDK')
def test_side_observation_and_wide_restore_respect_visible_screen(tmp_path):
    """窄版锚定可见屏幕右上，宽版恢复位置并在屏幕变化后约束边界。"""
    source = Path(__file__).resolve().parents[1] / 'native/StarDesktop/Sources/StarDesktop/WindowLayout.swift'
    harness = tmp_path / 'main.swift'
    harness.write_text('''import Foundation
import CoreGraphics
let screen = CGRect(x: 0, y: 33, width: 1440, height: 900)
let side = sideObservationFrame(in: screen)
precondition(side.size == CGSize(width: 520, height: 820))
precondition(side.maxX == screen.maxX && side.maxY == screen.maxY)
let external = CGRect(x: -1920, y: -100, width: 1920, height: 1080)
let externalSide = sideObservationFrame(in: external)
precondition(external.contains(externalSide))
precondition(externalSide.maxX == external.maxX && externalSide.maxY == external.maxY)
let small = CGRect(x: -300, y: 40, width: 300, height: 500)
precondition(sideObservationFrame(in: small) == small)
let original = CGRect(x: 10, y: 45, width: 1100, height: 850)
precondition(windowFrame(original, fitting: screen) == original)
let offscreen = CGRect(x: -500, y: -300, width: 1600, height: 1000)
precondition(windowFrame(offscreen, fitting: screen) == screen)
''')
    binary = tmp_path / 'layout'
    subprocess.run(['swiftc', '-module-cache-path', str(tmp_path / 'cache'), str(source), str(harness), '-o', str(binary)],
                   check=True, capture_output=True)
    subprocess.run([str(binary)], check=True)
