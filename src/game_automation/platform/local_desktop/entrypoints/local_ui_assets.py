"""读取本地控制 UI 的静态页面资源。

本 module 负责把受信任的静态资源名称映射到包内文件和 content type；它不处理
HTTP 请求、不调用 application 用例，也不解释 UI 交互语义。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

UI_STATIC_ROOT = Path(__file__).with_name("ui_static")


@dataclass(frozen=True, slots=True)
class UiAsset:
    body: bytes
    content_type: str


UI_ASSET_CONTENT_TYPES = {
    "index.html": "text/html; charset=utf-8",
    "control.css": "text/css; charset=utf-8",
    "control.js": "application/javascript; charset=utf-8",
}


def read_ui_asset(asset_name: str) -> UiAsset:
    """读取白名单内的 UI 静态资源。"""
    content_type = UI_ASSET_CONTENT_TYPES.get(asset_name)
    if content_type is None:
        raise FileNotFoundError(asset_name)
    asset_path = UI_STATIC_ROOT / asset_name
    if not asset_path.is_file():
        raise FileNotFoundError(asset_name)
    return UiAsset(body=asset_path.read_bytes(), content_type=content_type)
