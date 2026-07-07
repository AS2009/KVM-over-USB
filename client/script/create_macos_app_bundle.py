#!/usr/bin/env python3
"""创建 macOS .app 包裹，将 Nuitka standalone 输出打包为可双击启动的 .app。"""

import os
import plistlib
import shutil
import subprocess
import sys


def create_info_plist(contents_dir: str) -> None:
    """向 Contents 目录写入 Info.plist。"""
    plist = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleExecutable": "usb_kvm_client",
        "CFBundleIdentifier": "org.wevsty.usb-kvm-client",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": "USB KVM Client",
        "CFBundleDisplayName": "USB KVM Client",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "1.0",
        "CFBundleVersion": "1.0.0",
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Copyright (c) wevsty",
    }
    plist_path = os.path.join(contents_dir, "Info.plist")
    with open(plist_path, "wb") as f:
        plistlib.dump(plist, f)
    print(f"  Info.plist -> {plist_path}")


def create_icns(splash_png: str, resources_dir: str) -> bool:
    """从 splash.png 生成 app.icns 并写入 Resources。"""
    if not os.path.isfile(splash_png):
        print("  splash.png 未找到，跳过图标生成")
        return False

    iconset = "/tmp/app.iconset"
    os.makedirs(iconset, exist_ok=True)

    sizes = [16, 32, 128, 256]
    for size in sizes:
        dst = os.path.join(iconset, f"icon_{size}x{size}.png")
        subprocess.run(
            ["sips", "-z", str(size), str(size), splash_png, "--out", dst],
            capture_output=True,
        )

    icns_path = os.path.join(resources_dir, "app.icns")
    result = subprocess.run(
        ["iconutil", "-c", "icns", iconset, "-o", icns_path],
        capture_output=True,
    )
    shutil.rmtree(iconset, ignore_errors=True)

    if result.returncode == 0:
        print(f"  app.icns -> {icns_path}")
        return True
    return False


def main() -> None:
    if len(sys.argv) != 3:
        print("用法: create_macos_app_bundle.py <nuitka_dist_dir> <output_app_dir>")
        sys.exit(1)

    dist_dir = os.path.abspath(sys.argv[1])
    app_dir = os.path.abspath(sys.argv[2])

    if not os.path.isdir(dist_dir):
        print(f"错误: Nuitka 输出目录不存在: {dist_dir}")
        sys.exit(1)

    bundle_name = "USB KVM Client.app"
    bundle_path = os.path.join(app_dir, bundle_name)
    contents = os.path.join(bundle_path, "Contents")
    macos_dir = os.path.join(contents, "MacOS")
    resources_dir = os.path.join(contents, "Resources")

    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # 复制 Nuitka standalone 输出到 .app/MacOS
    print(f"复制 {dist_dir} -> {macos_dir}")
    for item in os.listdir(dist_dir):
        src = os.path.join(dist_dir, item)
        dst = os.path.join(macos_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)

    # 确保二进制可执行
    binary = os.path.join(macos_dir, "usb_kvm_client")
    if os.path.isfile(binary):
        os.chmod(binary, 0o755)

    # 生成 Info.plist
    create_info_plist(contents)

    # 生成图标
    splash_png = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "icons", "splash.png"
    )
    if create_icns(splash_png, resources_dir):
        # 在 Info.plist 中添加图标引用
        plist_path = os.path.join(contents, "Info.plist")
        subprocess.run(
            ["/usr/libexec/PlistBuddy",
             "-c", "Add :CFBundleIconFile string app.icns",
             plist_path],
            capture_output=True,
        )

    print(f"✅ .app 包裹创建完成: {bundle_path}")


if __name__ == "__main__":
    main()
