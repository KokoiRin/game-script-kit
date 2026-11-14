"""定义项目内可复用资源路径。

本 module 只保存本地项目 assets 目录、任务目录和图片后缀规则；
它不读取配置、不运行任务，也不创建 UI 或平台 adapter。
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
IMAGE_ASSET_FOLDER = "assets"
IMAGE_ASSET_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp"})
TASK_FOLDER = "scripts"


def image_asset_root(project_root: Path = PROJECT_ROOT) -> Path:
    """返回项目图片资源目录路径。"""
    return project_root / IMAGE_ASSET_FOLDER


def task_root(project_root: Path = PROJECT_ROOT) -> Path:
    """返回项目 Python 任务目录路径。"""
    return project_root / TASK_FOLDER
