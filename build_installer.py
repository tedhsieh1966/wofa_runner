# build_installer.py
import os
import platform
import PyInstaller.__main__
import shutil
from pathlib import Path
import sys
import subprocess
import glob
from app_info import *

# 添加根目錄到路徑
ROOT_DIR = str(Path(__file__).parent)
sys.path.insert(0, ROOT_DIR)

INSTALLER_NAME = APP_NAME + "_installer"
BUILD_DIR = os.path.join(ROOT_DIR, DIR_BUILD)


def build_installer_windows():
    """為 Windows 建立安裝程式"""
    print(f"開始建置安裝程式: {INSTALLER_NAME}")

    main_exe_path = os.path.join(ROOT_DIR, DIR_DIST, APP_EXE)
    if not os.path.exists(main_exe_path):
        print(f"❌ 錯誤: 主程式 {APP_EXE} 不存在，請先運行 build.py")
        return False

    # 確保資源文件存在
    required_files = [FP_LANGUAGES, FP_APP_ICON]
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ 錯誤: 檔案不存在 {file_path}")
            return False

    # 建立構建命令
    build_args = [
        "installer.py",  # 假設您有 installer.py
        '--onefile',
        '--windowed',
        f"--name={INSTALLER_NAME}",
        f"--icon={FP_APP_ICON}",
        f"--add-data={main_exe_path}{SEPARATOR}.",
        f"--add-data={FP_LANGUAGES}{SEPARATOR}.",
        f"--add-data={FP_APP_ICON}{SEPARATOR}.",
        f'--add-data={os.path.join(ROOT_DIR, "wofa")}{SEPARATOR}wofa',
        "--noconfirm",
        "--clean",
        f"--distpath={os.path.join(ROOT_DIR, 'dist')}",
        f"--workpath={os.path.join(ROOT_DIR, 'build')}",
    ]

    # 找出所有符合的檔案
    #wfa_files = glob.glob(os.path.join(ROOT_DIR, "wofa", "*.wfa"))
    # 為每個檔案生成 --add-data 參數
    #for f in wfa_files:
    #    # 這裡將檔案放在打包後的根目錄（.），或指定子目錄
    #    build_args.append(f'--add-data={f}{SEPARATOR}.')

    print("開始 PyInstaller 建置...")
    try:
        PyInstaller.__main__.run(build_args)
        print(f"✅ 安裝程式建置完成！")
        print(f"安裝程式位置: {os.path.join(ROOT_DIR, 'dist', INSTALLER_NAME)}.exe")
        return True
    except Exception as e:
        print(f"❌ 建置失敗: {e}")
        return False


def build_installer_mac():
    """為 macOS 建立安裝包 (PKG)"""
    print("開始建置 macOS 安裝包...")

    app_path = os.path.join(ROOT_DIR, DIR_DIST, f"{APP_NAME}.app")
    if not os.path.exists(app_path):
        print(f"❌ 錯誤: 找不到應用程式 {app_path}")
        return False

    try:
        # 使用 pkgbuild 建立 PKG
        pkg_name = f"{APP_NAME}.pkg"
        component_plist = "component.plist"

        # 建立 component.plist
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
    <dict>
        <key>BundleHasStrictIdentifier</key>
        <true/>
        <key>BundleIsRelocatable</key>
        <false/>
        <key>BundleIsVersionChecked</key>
        <true/>
        <key>BundleOverwriteAction</key>
        <string>upgrade</string>
        <key>RootRelativeBundlePath</key>
        <string>{APP_NAME}.app</string>
    </dict>
</array>
</plist>'''

        with open(component_plist, 'w') as f:
            f.write(plist_content)

        # 建立 PKG
        cmd = [
            'pkgbuild',
            '--component', app_path,
            '--install-location', '/Applications',
            '--identifier', f'com.example.{APP}',
            '--version', '1.0.0',
            '--ownership', 'recommended',
            pkg_name
        ]

        subprocess.run(cmd, check=True)
        print(f"✅ PKG 安裝包建立完成: {pkg_name}")

        # 清理臨時檔案
        if os.path.exists(component_plist):
            os.remove(component_plist)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 建立 PKG 失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def build_installer_linux():
    """為 Linux 建立 DEB 包 (適用於 Debian/Ubuntu)"""
    print("開始建置 Linux DEB 包...")

    # 檢查必要工具
    required_tools = ['dpkg-deb', 'fakeroot']
    for tool in required_tools:
        try:
            subprocess.run(['which', tool], capture_output=True, check=True)
        except subprocess.CalledProcessError:
            print(f"❌ 錯誤: 未安裝 {tool}")
            print(f"請執行: sudo apt-get install {tool}")
            return False

    # 建立 DEB 包結構
    deb_dir = f"{APP_NAME}_deb"
    if os.path.exists(deb_dir):
        shutil.rmtree(deb_dir)

    # 建立目錄結構
    os.makedirs(os.path.join(deb_dir, "DEBIAN"), exist_ok=True)
    install_dir = os.path.join(deb_dir, "usr", "local", "bin")
    os.makedirs(install_dir, exist_ok=True)
    app_dir = os.path.join(deb_dir, "usr", "share", "applications")
    os.makedirs(app_dir, exist_ok=True)
    icon_dir = os.path.join(deb_dir, "usr", "share", "icons", "hicolor", "128x128", "apps")
    os.makedirs(icon_dir, exist_ok=True)

    # 複製可執行檔
    executable_path = os.path.join(ROOT_DIR, DIR_DIST, APP_NAME)
    if os.path.exists(executable_path):
        shutil.copy(executable_path, os.path.join(install_dir, APP_NAME))
        os.chmod(os.path.join(install_dir, APP_NAME), 0o755)

    # 建立 desktop 檔案
    desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment={DESCRIPTION}
Exec=/usr/local/bin/{APP_NAME}
Icon={APP_NAME}
Terminal=false
Type=Application
Categories=Utility;
"""

    with open(os.path.join(app_dir, f"{APP_NAME}.desktop"), 'w') as f:
        f.write(desktop_content)

    # 複製圖標
    if os.path.exists(FP_APP_ICON):
        shutil.copy(FP_APP_ICON, os.path.join(icon_dir, f"{APP_NAME}.png"))

    # 建立 control 檔案
    control_content = f"""Package: {APP}
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Your Name <your.email@example.com>
Description: {DESCRIPTION}
 {BRIEF}
"""

    with open(os.path.join(deb_dir, "DEBIAN", "control"), 'w') as f:
        f.write(control_content)

    # 建立 postinst 腳本 (可選)
    postinst_content = """#!/bin/bash
# 安裝後腳本
update-desktop-database /usr/share/applications
"""

    with open(os.path.join(deb_dir, "DEBIAN", "postinst"), 'w') as f:
        f.write(postinst_content)
    os.chmod(os.path.join(deb_dir, "DEBIAN", "postinst"), 0o755)

    # 建立 DEB 包
    try:
        deb_file = f"{APP_NAME}_1.0.0_amd64.deb"
        cmd = ['fakeroot', 'dpkg-deb', '--build', deb_dir, deb_file]
        subprocess.run(cmd, check=True)
        print(f"✅ DEB 包建立完成: {deb_file}")

        # 清理臨時目錄
        shutil.rmtree(deb_dir)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 建立 DEB 包失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def build_installer():
    """跨平台安裝程式建置"""
    system = platform.system()

    print(f"開始建置 {system} 安裝程式...")

    if system == "Windows":
        return build_installer_windows()
    elif system == "Darwin":
        return build_installer_mac()
    elif system == "Linux":
        return build_installer_linux()
    else:
        print(f"❌ 不支援的操作系統: {system}")
        return False


if __name__ == "__main__":
    success = build_installer()
    sys.exit(0 if success else 1)