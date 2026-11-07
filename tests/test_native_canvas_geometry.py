"""验证原生拖框端点的像素几何。

本 module 仅编译 Foundation 纯函数，不创建窗口或读取桌面；
非 macOS 环境跳过本机 Swift SDK 验证。
"""

from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='requires macOS Swift SDK')
def test_drag_includes_last_pixel_in_both_directions(tmp_path):
    """全图、反向和单像素框选都保留包含式端点。"""
    source = Path(__file__).resolve().parents[1] / 'native/StarDesktop/Sources/StarDesktop/CanvasGeometry.swift'
    harness = tmp_path / 'main.swift'
    harness.write_text('''import Foundation
let entire = PixelRegion(left: 0, top: 0, width: 160, height: 120)
precondition(canvasRegion(CGPoint(x: 0, y: 0), CGPoint(x: 159, y: 119)) == entire)
precondition(canvasRegion(CGPoint(x: 159, y: 119), CGPoint(x: 0, y: 0)) == entire)
precondition(canvasRegion(CGPoint(x: 159, y: 119), CGPoint(x: 159, y: 119)) == PixelRegion(left: 159, top: 119, width: 1, height: 1))
''')
    binary = tmp_path / 'geometry'
    subprocess.run(['swiftc', '-module-cache-path', str(tmp_path / 'cache'), str(source), str(harness), '-o', str(binary)], check=True, capture_output=True)
    subprocess.run([str(binary)], check=True)
