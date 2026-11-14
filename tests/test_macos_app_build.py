"""验证本地应用构建的系统兼容性和后台定位。

本 module 用编译器替身检查生成应用的公开产物，不运行系统编译器或签名工具，
也不改动用户的 Applications 目录。
"""

import importlib.util
import plistlib
from pathlib import Path

import pytest


@pytest.fixture
def builder():
    """加载构建入口而不执行构建。"""
    path = Path(__file__).resolve().parents[1] / "tools/build_macos_app.py"
    spec = importlib.util.spec_from_file_location("star_app_builder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("architecture", ["arm64", "x86_64"])
def test_direct_build_keeps_supported_target_and_backend_location(
    builder, tmp_path, monkeypatch, architecture
):
    """编译器默认目标过高时，应用仍按 macOS 13 构建且绑定正确源代码。"""
    root = tmp_path / "checkout"
    source = root / "native/StarDesktop/Sources/StarDesktop/Main.swift"
    source.parent.mkdir(parents=True)
    source.write_text("source")
    output = tmp_path / "Applications/Star.app"
    calls = []

    def run(command, **kwargs):
        """模拟编译产物，保留结构化构建及签名命令供核对。"""
        calls.append(command)
        if command[0] == "swiftc":
            binary = Path(command[command.index("-o") + 1])
            binary.write_bytes(b"native")
            binary.chmod(0o755)

    monkeypatch.setattr(builder.platform, "machine", lambda: architecture)
    monkeypatch.setattr(builder.subprocess, "run", run)
    assert (
        builder.build_app(
            root, python="/env/bin/python", output=output, compiler="swiftc"
        )
        == output
    )
    assert f"{architecture}-apple-macosx13.0" in calls[0]
    assert (output / "Contents/MacOS/StarDesktop").read_bytes() == b"native"
    with (output / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    assert info["StarSourceRoot"] == str(root)
    assert info["StarPython"] == "/env/bin/python"
    assert info["CFBundleIdentifier"] == "com.kokoirin.star"
    assert calls[-2][:5] == ["codesign", "--force", "--timestamp=none", "--sign", "-"]
    assert calls[-1][:3] == ["codesign", "--verify", "--strict"]
    assert calls[-1][-1] != str(output)


def test_direct_build_rejects_empty_sources_without_launching_compiler(
    builder, tmp_path, monkeypatch
):
    """源代码缺失时不生成看似可安装的空应用。"""
    monkeypatch.setattr(builder.platform, "machine", lambda: "arm64")
    with pytest.raises(ValueError, match="sources"):
        builder.build_app(
            tmp_path, python="/python", output=tmp_path / "Star.app", compiler="swiftc"
        )


def test_signing_configuration_priority_and_file_validation(builder, tmp_path):
    """命令行优先于环境和文件，文件只接受完整证书指纹。"""
    identity_file = tmp_path / "Library/Application Support/Star/signing/identity"
    identity_file.parent.mkdir(parents=True)
    identity_file.write_text("a" * 40 + "\n")
    assert (
        builder.resolve_signing_identity(
            "CLI", environ={"STAR_SIGNING_IDENTITY": "ENV"}, home=tmp_path
        )
        == "CLI"
    )
    assert (
        builder.resolve_signing_identity(
            environ={"STAR_SIGNING_IDENTITY": "ENV"}, home=tmp_path
        )
        == "ENV"
    )
    assert builder.resolve_signing_identity(environ={}, home=tmp_path) == "a" * 40
    identity_file.write_text("certificate name")
    with pytest.raises(ValueError, match="40"):
        builder.resolve_signing_identity(environ={}, home=tmp_path)
    identity_file.unlink()
    assert builder.resolve_signing_identity(environ={}, home=tmp_path) == "-"
    with pytest.raises(ValueError):
        builder.resolve_signing_identity(
            environ={"STAR_SIGNING_IDENTITY": ""}, home=tmp_path
        )


def test_signing_failure_preserves_existing_installation(
    builder, tmp_path, monkeypatch
):
    """签名失败保留旧安装，且不会再次尝试临时签名。"""
    import subprocess

    root = tmp_path / "checkout"
    source = root / "native/StarDesktop/Sources/StarDesktop/Main.swift"
    source.parent.mkdir(parents=True)
    source.write_text("source")
    output = tmp_path / "Star.app"
    output.mkdir()
    (output / "old").write_text("keep")
    calls = []

    def run(command, **kwargs):
        """模拟编译成功及证书签名失败。"""
        calls.append(command)
        if command[0] == "swiftc":
            Path(command[command.index("-o") + 1]).write_bytes(b"native")
        else:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(builder.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(builder.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        builder.build_app(
            root,
            python="/python",
            output=output,
            compiler="swiftc",
            signing_identity="fixed",
        )
    assert (output / "old").read_text() == "keep"
    signs = [command for command in calls if command[0] == "codesign"]
    assert len(signs) == 1
    assert signs[0][signs[0].index("--sign") + 1] == "fixed"


def test_verification_changes_only_copy_and_checks_old_requirement(
    builder, tmp_path, monkeypatch
):
    """跨内容验证只修改副本，并要求新副本满足旧指定要求。"""
    from types import SimpleNamespace

    app = tmp_path / "Star.app"
    (app / "Contents").mkdir(parents=True)
    original = plistlib.dumps({"CFBundleVersion": "1"})
    (app / "Contents/Info.plist").write_bytes(original)
    calls = []

    def run(command, **kwargs):
        """返回同一证书要求及两个不同内容散列。"""
        calls.append(command)
        target = Path(command[-1])
        if "--sign" in command:
            assert target != app
            assert (
                plistlib.loads((target / "Contents/Info.plist").read_bytes())[
                    "CFBundleVersion"
                ]
                != "1"
            )
        if "--requirements" in command:
            return SimpleNamespace(
                stdout="",
                stderr='designated => identifier "com.kokoirin.star" and anchor trusted\n',
            )
        if "--verbose=4" in command:
            return SimpleNamespace(
                stdout="",
                stderr="CDHash=" + ("a" if target == app else "b") * 40 + "\n",
            )
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(builder.subprocess, "run", run)
    builder.verify_signing(app, "fixed")
    assert (app / "Contents/Info.plist").read_bytes() == original
    assert any(
        any(arg.startswith("-R=identifier") for arg in command) for command in calls
    )
    with pytest.raises(ValueError, match="固定"):
        builder.verify_signing(app, "-")


@pytest.mark.parametrize(
    "failure",
    ["requirement_changed", "cdhash_requirement", "hash_unchanged", "strict_verify"],
)
def test_unstable_signature_fails_verification_without_touching_original(
    builder, tmp_path, monkeypatch, failure
):
    """身份要求、内容或签名校验异常都失败，不改原应用。"""
    import subprocess
    from types import SimpleNamespace

    app = tmp_path / "Star.app"
    (app / "Contents").mkdir(parents=True)
    original = plistlib.dumps({"CFBundleVersion": "1"})
    (app / "Contents/Info.plist").write_bytes(original)

    def run(command, **kwargs):
        """分别模拟不稳定签名和严格校验失败。"""
        target = Path(command[-1])
        if "--requirements" in command:
            requirement = 'identifier "star" and anchor trusted'
            if failure == "requirement_changed" and target != app:
                requirement += ' and certificate leaf = H"abc"'
            if failure == "cdhash_requirement":
                requirement += ' and cdhash H"abc"'
            return SimpleNamespace(stdout="", stderr="designated => " + requirement)
        if "--verbose=4" in command:
            content = "a" if target == app or failure == "hash_unchanged" else "b"
            return SimpleNamespace(stdout="", stderr="CDHash=" + content * 40)
        if "--verify" in command and failure == "strict_verify":
            raise subprocess.CalledProcessError(1, command)
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr(builder.subprocess, "run", run)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        builder.verify_signing(app, "fixed")
    assert (app / "Contents/Info.plist").read_bytes() == original


def test_strict_signing_check_failure_preserves_old_install(
    builder, tmp_path, monkeypatch
):
    """签名命令成功但严格验证失败也不能替换旧安装。"""
    import subprocess

    root = tmp_path / "checkout"
    source = root / "native/StarDesktop/Sources/StarDesktop/Main.swift"
    source.parent.mkdir(parents=True)
    source.write_text("source")
    output = tmp_path / "Star.app"
    output.mkdir()
    (output / "old").write_text("keep")

    def run(command, **kwargs):
        """模拟签名成功、校验失败，并检查失败前旧包仍在。"""
        assert (output / "old").read_text() == "keep"
        if command[0] == "swiftc":
            Path(command[command.index("-o") + 1]).write_bytes(b"native")
        elif "--verify" in command:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(builder.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(builder.subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        builder.build_app(
            root,
            python="/python",
            output=output,
            compiler="swiftc",
            signing_identity="fixed",
        )
    assert (output / "old").read_text() == "keep"


def test_cli_resolves_identity_and_enables_verification(builder, tmp_path, monkeypatch):
    """命令行把固定身份与验证选项交给构建边界。"""
    calls = []

    def build(root, **kwargs):
        """记录参数而不调用真实编译器或签名工具。"""
        calls.append(kwargs)
        return kwargs["output"]

    monkeypatch.setattr(builder.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(builder, "build_app", build)
    monkeypatch.setenv("STAR_SIGNING_IDENTITY", "ENV")
    assert builder.main(["--signing-identity", "CLI", "--verify-signing"]) == 0
    assert calls[0]["signing_identity"] == "CLI"
    assert calls[0]["verify"] is True


def test_adhoc_verification_rejected_before_compiling(builder, tmp_path, monkeypatch):
    """临时签名不能执行身份稳定性验证，也不先启动编译。"""

    def run(*args, **kwargs):
        """阻止任何系统命令被执行。"""
        pytest.fail("must reject before launching commands")

    monkeypatch.setattr(builder.subprocess, "run", run)
    with pytest.raises(ValueError, match="固定"):
        builder.build_app(
            tmp_path,
            python="/python",
            output=tmp_path / "Star.app",
            signing_identity="-",
            verify=True,
        )


@pytest.mark.parametrize("restore_fails", [False, True])
def test_failed_install_restores_or_retains_old_bundle(
    builder, tmp_path, monkeypatch, restore_fails
):
    """替换失败时恢复旧包；恢复也失败时在自动清理范围外保留旧包。"""
    root = tmp_path / "checkout"
    source = root / "native/StarDesktop/Sources/StarDesktop/Main.swift"
    source.parent.mkdir(parents=True)
    source.write_text("source")
    output = tmp_path / "Star.app"
    output.mkdir()
    (output / "old").write_text("keep")
    original_rename = Path.rename

    def rename(path, target):
        """仅阻止新包安装及可选旧包恢复，允许最初备份。"""
        if Path(target) == output:
            is_old = (path / "old").exists()
            if not is_old or restore_fails:
                raise OSError("restore denied" if is_old else "install denied")
        return original_rename(path, target)

    def run(command, **kwargs):
        """模拟构建签名成功，错误只发生于安装替换。"""
        if command[0] == "swiftc":
            Path(command[command.index("-o") + 1]).write_bytes(b"native")

    monkeypatch.setattr(builder.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(builder.subprocess, "run", run)
    monkeypatch.setattr(Path, "rename", rename)
    with pytest.raises(OSError) as error:
        builder.build_app(
            root,
            python="/python",
            output=output,
            compiler="swiftc",
            signing_identity="fixed",
        )
    if restore_fails:
        retained = list(tmp_path.glob(".star-backup-*/Star.app/old"))
        assert len(retained) == 1
        assert retained[0].read_text() == "keep"
        assert str(retained[0].parent) in str(error.value)
        assert not output.exists()
    else:
        assert (output / "old").read_text() == "keep"
        assert "install denied" in str(error.value)
        assert not list(tmp_path.glob(".star-backup-*"))
    assert not list(tmp_path.glob(".star-build-*"))
