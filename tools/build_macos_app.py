"""构建或安装绑定当前 checkout 和 Python 环境的开发用 Star.app。

本工具编译原生壳并使用显式配置的本机签名身份；不打包 Python、管理证书，
不执行脚本或申请桌面权限。可显式选择 swiftc 以绕开本机 SwiftPM 不兼容。
"""

import argparse
import os
import re
import tempfile
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys


def build_app(root: Path, *, python: str, output: Path, compiler: str = 'swiftpm',
              signing_identity: str = '-', verify: bool = False) -> Path:
    """编译并组装开发应用，固定最低系统版本和后台源代码位置。"""
    identity = _validate_identity(signing_identity)
    if verify and identity == '-':
        raise ValueError('签名稳定性验证需要固定签名身份，不能使用 ad-hoc')
    if identity == '-':
        print('警告：未使用固定签名身份，正在使用 ad-hoc 临时签名；重编译后 macOS 权限可能失效。', file=sys.stderr)
    package = root / 'native/StarDesktop'
    if compiler == 'swiftpm':
        command = ['swift', 'build', '--package-path', str(package), '-c', 'release']
        subprocess.run(command, check=True)
        binaries = Path(subprocess.check_output(command + ['--show-bin-path'], text=True).strip())
        binary = binaries / 'StarDesktop'
    elif compiler == 'swiftc':
        architecture = platform.machine()
        if architecture not in {'arm64', 'x86_64'}:
            raise ValueError(f'unsupported macOS architecture: {architecture}')
        binary = package / '.build/direct/StarDesktop'
        binary.parent.mkdir(parents=True, exist_ok=True)
        sources = sorted((package / 'Sources/StarDesktop').glob('*.swift'))
        if not sources:
            raise ValueError('StarDesktop Swift sources not found')
        subprocess.run([
            'swiftc', '-target', f'{architecture}-apple-macosx13.0', '-parse-as-library', '-O',
            *map(str, sources), '-o', str(binary), '-framework', 'SwiftUI', '-framework', 'AppKit',
        ], check=True)
    else:
        raise ValueError(f'unknown compiler: {compiler}')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.star-build-', dir=output.parent) as staging:
        staged = Path(staging) / 'Star.app'
        contents = staged / 'Contents'
        executable = contents / 'MacOS/StarDesktop'
        executable.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, executable)
        info = {
            'CFBundleIdentifier': 'com.kokoirin.star', 'CFBundleName': 'Star',
            'CFBundleExecutable': 'StarDesktop', 'CFBundlePackageType': 'APPL',
            'CFBundleShortVersionString': '0.1.0', 'CFBundleVersion': '1',
            'LSMinimumSystemVersion': '13.0', 'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.developer-tools',
            'StarPython': python, 'StarSourceRoot': str(root),
        }
        with (contents / 'Info.plist').open('wb') as destination:
            plistlib.dump(info, destination)
        _sign(staged, identity)
        subprocess.run(['codesign', '--verify', '--strict', str(staged)], check=True)
        if verify:
            verify_signing(staged, identity)
        backup_directory = None
        if output.exists() or output.is_symlink():
            backup_directory = Path(tempfile.mkdtemp(prefix='.star-backup-', dir=output.parent))
            backup = backup_directory / 'Star.app'
            try:
                output.rename(backup)
            except BaseException:
                backup_directory.rmdir()
                raise
        try:
            staged.rename(output)
        except BaseException as install_error:
            if backup_directory is not None:
                try:
                    backup.rename(output)
                except BaseException as restore_error:
                    raise OSError(f'安装失败（{install_error}），恢复也失败（{restore_error}）；'
                                  f'旧版应用保留于：{backup}') from restore_error
                backup_directory.rmdir()
            raise
        if backup_directory is not None:
            shutil.rmtree(backup_directory)
    return output


def _validate_identity(identity: str) -> str:
    """拒绝显式空配置，防止误用默认签名。"""
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError('签名身份不能为空')
    return identity.strip()


def resolve_signing_identity(identity: str | None = None, *, environ=None, home: Path | None = None) -> str:
    """按命令行、环境、固定文件的顺序解析身份，缺省才使用临时签名。"""
    if identity is not None:
        return _validate_identity(identity)
    environment = os.environ if environ is None else environ
    if 'STAR_SIGNING_IDENTITY' in environment:
        return _validate_identity(environment['STAR_SIGNING_IDENTITY'])
    path = (Path.home() if home is None else home) / 'Library/Application Support/Star/signing/identity'
    if path.exists() or path.is_symlink():
        value = path.read_text(encoding='utf-8').strip()
        if re.fullmatch(r'[0-9a-fA-F]{40}', value) is None:
            raise ValueError(f'签名身份文件必须只包含 40 位十六进制证书指纹：{path}')
        return value
    return '-'


def _sign(application: Path, identity: str) -> None:
    """使用指定身份签名，失败直接传播且不降级。"""
    subprocess.run(['codesign', '--force', '--timestamp=none', '--sign', identity, str(application)], check=True)


def _signature_field(application: Path, *, requirement: bool) -> str:
    """读取指定要求或内容散列，兼容 codesign 的标准错误输出。"""
    options = ['--requirements', '-'] if requirement else ['--verbose=4']
    result = subprocess.run(['codesign', '--display', *options, str(application)],
                            check=True, capture_output=True, text=True)
    prefix = 'designated => ' if requirement else 'CDHash='
    values = [line[len(prefix):].strip() for line in (result.stdout + '\n' + result.stderr).splitlines()
              if line.startswith(prefix)]
    if len(values) != 1 or not values[0]:
        raise ValueError('无法读取应用的签名要求或内容散列')
    return values[0]


def verify_signing(application: Path, identity: str) -> None:
    """只重签临时副本，证明不同内容仍满足同一证书身份。"""
    identity = _validate_identity(identity)
    if identity == '-':
        raise ValueError('签名稳定性验证需要固定签名身份，不能使用 ad-hoc')
    before = _signature_field(application, requirement=True)
    first_hash = _signature_field(application, requirement=False)
    if re.search(r'\bcdhash\b', before, re.IGNORECASE):
        raise ValueError('应用指定要求绑定 cdhash，缺少稳定证书身份')
    with tempfile.TemporaryDirectory(prefix='star-signing-verify-') as staging:
        copy = Path(staging) / 'Star.app'
        shutil.copytree(application, copy, symlinks=True)
        info_path = copy / 'Contents/Info.plist'
        with info_path.open('rb') as stream:
            info = plistlib.load(stream)
        info['CFBundleVersion'] = str(info.get('CFBundleVersion', '')) + '.signing-verification'
        with info_path.open('wb') as stream:
            plistlib.dump(info, stream)
        _sign(copy, identity)
        after = _signature_field(copy, requirement=True)
        second_hash = _signature_field(copy, requirement=False)
        if before != after or re.search(r'\bcdhash\b', after, re.IGNORECASE):
            raise ValueError('应用内容改变后指定要求发生变化，签名身份不稳定')
        if first_hash == second_hash:
            raise ValueError('验证副本内容散列未改变，无法证明跨内容签名稳定')
        subprocess.run(['codesign', '--verify', '--strict', str(application)], check=True)
        subprocess.run(['codesign', '--verify', '--strict', '-R=' + before, str(copy)], check=True)


def main(argv: list[str] | None = None) -> int:
    """提供固定路径安装选项和显式的本机编译方式选择。"""
    parser = argparse.ArgumentParser(description='构建 Star macOS 开发应用')
    parser.add_argument('--compiler', choices=('swiftpm', 'swiftc'), default='swiftpm')
    parser.add_argument('--install', action='store_true', help='安装到当前用户的 Applications/Star.app')
    parser.add_argument('--signing-identity', help='固定签名身份或证书指纹，优先于环境与配置文件')
    parser.add_argument('--verify-signing', action='store_true', help='重签临时副本并验证跨内容身份稳定，不启动副本')
    args = parser.parse_args(argv)
    if platform.system() != 'Darwin':
        print('Star.app 必须在 macOS 上构建。', file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    output = Path.home() / 'Applications/Star.app' if args.install else root / 'native/StarDesktop/dist/Star.app'
    try:
        identity = resolve_signing_identity(args.signing_identity)
        application = build_app(root, python=sys.executable, output=output, compiler=args.compiler,
                                signing_identity=identity, verify=args.verify_signing)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f'Star.app 构建失败：{exc}', file=sys.stderr)
        return 1
    print(application)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
