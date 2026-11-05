"""装配本地素材准备服务。

本 module 只连接准备端口与平台 adapter；不导入运行控制台、脚本 catalog 或 runner。
"""

from pathlib import Path

from game_automation.portable.preparation.service import PreparationService


def build_preparation_service(workspace: Path) -> PreparationService:
    """构造设备依赖延迟加载的准备服务，绑定外部素材工作区。"""
    from game_automation.platform.desktop.adapters.preparation import DesktopFrameCapture, PillowImageEditor, WorkspaceTemplateStore
    from game_automation.platform.macos.adapters.preparation_windows import MacOSPreparationWindows

    return PreparationService(
        windows=MacOSPreparationWindows(), capture=DesktopFrameCapture(),
        images=PillowImageEditor(), templates=WorkspaceTemplateStore(workspace),
    )
