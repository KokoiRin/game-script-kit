"""定义项目内可复用资源路径。

本 module 只保存本地项目 assets 目录、状态配置文件名和图片后缀规则；
它不读取配置、不运行脚本，也不创建 UI 或平台 adapter。
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]
IMAGE_ASSET_FOLDER = "assets"
IMAGE_ASSET_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
SCREEN_STATE_CONFIG_NAME = "screen-states.json"


def image_asset_root(project_root: Path = PROJECT_ROOT) -> Path:
    """返回项目图片资源目录路径。"""
    return project_root / IMAGE_ASSET_FOLDER


def screen_state_config_path(project_root: Path = PROJECT_ROOT) -> Path:
    """返回项目状态识别配置文件路径。"""
    return image_asset_root(project_root) / SCREEN_STATE_CONFIG_NAME
