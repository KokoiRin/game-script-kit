"""验证准备入口选择工作区并保持脚本目录加载独立。

本 module 只测试命令映射，不启动真实桌面或长期 HTTP 服务。
"""

from game_automation.platform.local_desktop.entrypoints import cli, desktop_app


def test_prepare_requires_explicit_task_workspace(capsys):
    """准备素材时要求显式任务根，避免把业务资源写入框架仓库。"""
    assert cli.main(["prepare"]) == 2
    assert "requires --workspace" in capsys.readouterr().err


def test_prepare_starts_without_loading_script_catalog(tmp_path, monkeypatch):
    """准备入口仅向准备壳传递工作区，不读取坏脚本或构造运行应用。"""
    captured = {}

    def serve(**kwargs):
        """记录准备壳启动参数。"""
        captured.update(kwargs)
        return 0

    def reject(*args, **kwargs):
        """准备流程不能调用脚本加载。"""
        raise AssertionError("loaded scripts during preparation")

    monkeypatch.setattr(desktop_app, "launch_desktop", serve)
    monkeypatch.setattr(cli, "_load_cli_script_catalog_result", reject)
    assert cli.main(["--workspace", str(tmp_path), "prepare"]) == 0
    assert captured == {"workspace": tmp_path}
