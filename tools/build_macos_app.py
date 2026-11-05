"""构建开发用 Star.app，绑定当前 checkout 与 Python 环境。

本工具只生成原生启动壳，不打包 Python 解释器、发布应用或申请代码签名。
"""

from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys


def main() -> int:
    """在 macOS 上构建 Swift release 产物并生成可从 Finder 打开的应用。"""
    if platform.system() != "Darwin":
        print("Star.app 必须在 macOS 上构建。", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parents[1]
    package = root / "native/StarDesktop"
    command = ["swift", "build", "--package-path", str(package), "-c", "release"]
    subprocess.run(command, check=True)
    binaries = Path(subprocess.check_output(command + ["--show-bin-path"], text=True).strip())
    application = package / "dist/Star.app"
    contents = application / "Contents"
    executable = contents / "MacOS/StarDesktop"
    executable.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binaries / "StarDesktop", executable)
    info = {
        "CFBundleIdentifier": "com.kokoirin.star", "CFBundleName": "Star",
        "CFBundleExecutable": "StarDesktop", "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "0.1.0", "CFBundleVersion": "1",
        "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.developer-tools",
        "StarPython": sys.executable, "StarSourceRoot": str(root),
    }
    with (contents / "Info.plist").open("wb") as output:
        plistlib.dump(info, output)
    print(application)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
