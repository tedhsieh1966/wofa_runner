#!/usr/bin/env python3
# build_mobile.py - 簡化版行動端建置工具

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path
import json

# 專案配置
ROOT_DIR = Path(__file__).parent
SRC_DIR = ROOT_DIR / "src"
MOBILE_DIR = ROOT_DIR / "mobile"

APP_NAME = "WfaRunner"
APP_VERSION = "1.0.0"
APP_PACKAGE = "com.syntak.wfarunner"


def check_dependencies():
    """檢查必要的開發工具"""
    print("檢查依賴工具...")

    required_tools = ["python3", "pip3", "git"]
    if platform.system() == "Linux":
        required_tools.append("adb")

    missing_tools = []
    for cmd in required_tools:
        try:
            subprocess.run(["which", cmd], capture_output=True, check=True)
            print(f"✅ {cmd}")
        except:
            missing_tools.append(cmd)
            print(f"❌ {cmd}")

    return missing_tools


def setup_kivy_environment():
    """設定 Kivy 開發環境"""
    print("\n設定 Kivy 環境...")

    # 只安裝必要的套件
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "kivy", "buildozer"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"安裝失敗: {e}")
        return False


def create_mobile_main():
    """建立行動端的主程式檔案"""
    print("\n建立行動端主程式...")

    mobile_main_content = '''#!/usr/bin/env python3
# mobile/main.py - 行動端入口點

import os
import sys
from pathlib import Path

# 添加桌面端模組路徑
desktop_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(desktop_path))

def mobile_main():
    """行動端主函數"""
    print(f"啟動 {APP_NAME} 行動版...")

    try:
        # 嘗試匯入桌面端主程式
        import main
        print("成功載入桌面端模組")

        # 這裡可以根據平台調整
        if hasattr(main, 'main'):
            main.main()
        else:
            print("警告: 未找到 main.main() 函數")

    except ImportError as e:
        print(f"匯入桌面端模組失敗: {e}")
        print("請確保 src/main.py 存在")
        sys.exit(1)
    except Exception as e:
        print(f"執行錯誤: {e}")

if __name__ == "__main__":
    mobile_main()
'''

    # 建立 mobile 目錄
    MOBILE_DIR.mkdir(exist_ok=True)

    # 寫入主程式
    with open(MOBILE_DIR / "main.py", "w", encoding="utf-8") as f:
        f.write(mobile_main_content.replace("{APP_NAME}", APP_NAME))

    print(f"✅ 行動端主程式建立完成: {MOBILE_DIR / 'main.py'}")


def create_buildozer_spec():
    """建立 Buildozer 規格檔案 (Android)"""
    print("\n建立 Buildozer 規格檔案...")

    spec_content = f"""[app]

# 應用程式設定
title = {APP_NAME}
package.name = {APP_PACKAGE}
package.domain = com.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,txt,xlsx,json
version = {APP_VERSION}
requirements = python3,kivy

# 權限設定
android.permissions = INTERNET

# Android 設定
android.api = 31
android.minapi = 21

# 圖標（如果存在）
icon.filename = %(source.dir)s/../src/syntak_blue_128.png

# 方向設定
orientation = portrait

# 完整螢幕
fullscreen = 0

# 打包設定
android.accept_sdk_license = True
"""

    spec_file = MOBILE_DIR / "buildozer.spec"
    with open(spec_file, "w", encoding="utf-8") as f:
        f.write(spec_content)

    print(f"✅ Buildozer 規格檔案建立完成: {spec_file}")


def build_android():
    """建置 Android APK"""
    print("\n開始建置 Android APK...")

    # 切換到 mobile 目錄
    original_dir = os.getcwd()
    os.chdir(MOBILE_DIR)

    try:
        # 初始化 Buildozer
        print("初始化 Buildozer...")
        subprocess.run(["buildozer", "init"], check=True)

        # 建置 debug 版本
        print("建置 Debug 版本...")
        subprocess.run(["buildozer", "-v", "android", "debug"], check=True)

        # 尋找生成的 APK
        bin_dir = Path("bin")
        if bin_dir.exists():
            apk_files = list(bin_dir.glob("*.apk"))
            if apk_files:
                print(f"✅ Android APK 建置完成:")

                # 建立輸出目錄
                output_dir = ROOT_DIR / "dist" / "android"
                output_dir.mkdir(parents=True, exist_ok=True)

                # 複製 APK 檔案
                for apk in apk_files:
                    shutil.copy(apk, output_dir / apk.name)
                    print(f"   → {output_dir / apk.name}")

                return True
            else:
                print("❌ 未找到生成的 APK 檔案")
                return False
        else:
            print("❌ bin 目錄不存在")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ Android 建置失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False
    finally:
        # 返回原始目錄
        os.chdir(original_dir)


def build_ios_simple():
    """簡化的 iOS 建置指引"""
    print("\n=== iOS 建置指引 ===")
    print("iOS 建置需要 macOS 和 Xcode，以下是簡化步驟：")
    print()
    print("1. 安裝必要工具 (在 macOS 上):")
    print("   brew install autoconf automake libtool pkg-config")
    print("   pip3 install kivy-ios")
    print()
    print("2. 建立 iOS 專案:")
    print(f"   cd {MOBILE_DIR}")
    print(f"   toolchain create {APP_NAME} {APP_PACKAGE}")
    print()
    print("3. 新增您的程式:")
    print(f"   cp main.py {APP_NAME}/")
    print()
    print("4. 編譯專案:")
    print(f"   cd {APP_NAME}")
    print(f"   toolchain build {APP_NAME}")
    print()
    print("5. 在 Xcode 中開啟專案並執行")
    print()
    print("注意: iOS 模擬器需要簽名才能執行")
    return False


def create_desktop_to_mobile_bridge():
    """建立桌面端到行動端的橋接器"""
    print("\n建立桌面端到行動端橋接器...")

    bridge_content = '''#!/usr/bin/env python3
# mobile_bridge.py - 桌面/行動端共用橋接器

import sys
import os

def is_mobile():
    """檢查是否在移動設備上"""
    # 偵測 Android
    if 'ANDROID_ARGUMENT' in os.environ:
        return 'android'
    # 偵測 iOS (Kivy)
    elif sys.platform == 'ios' or 'ios' in sys.platform:
        return 'ios'
    return None

def get_platform_config():
    """取得平台配置"""
    platform_type = is_mobile()

    config = {
        'is_mobile': bool(platform_type),
        'platform': platform_type or 'desktop',
        'ui_scale': 1.0,
        'touch_mode': False,
        'screen_size': (800, 600)  # 預設大小
    }

    # 行動端調整
    if platform_type == 'android':
        config.update({
            'ui_scale': 1.5,
            'touch_mode': True,
            'screen_size': (360, 640)  # 典型手機尺寸
        })
    elif platform_type == 'ios':
        config.update({
            'ui_scale': 1.5,
            'touch_mode': True,
            'screen_size': (375, 667)  # iPhone 典型尺寸
        })

    return config

def adapt_ui_for_platform():
    """根據平台調整 UI"""
    config = get_platform_config()

    print(f"平台: {config['platform']}")
    print(f"螢幕尺寸: {config['screen_size']}")
    print(f"觸控模式: {config['touch_mode']}")

    return config

# 匯出配置
PLATFORM_CONFIG = adapt_ui_for_platform()
IS_MOBILE = PLATFORM_CONFIG['is_mobile']
PLATFORM = PLATFORM_CONFIG['platform']
'''

    bridge_file = MOBILE_DIR / "mobile_bridge.py"
    with open(bridge_file, "w", encoding="utf-8") as f:
        f.write(bridge_content)

    print(f"✅ 橋接器建立完成: {bridge_file}")
    return True


def main():
    """主函數"""
    print(f"=== {APP_NAME} 行動端建置工具 (簡化版) ===\n")

    # 檢查依賴
    missing = check_dependencies()
    if missing:
        print(f"\n❌ 缺少必要工具: {', '.join(missing)}")
        return False

    # 建立 mobile 目錄結構
    MOBILE_DIR.mkdir(exist_ok=True)

    # 建立橋接器
    create_desktop_to_mobile_bridge()

    # 建立行動端主程式
    create_mobile_main()

    print("\n請選擇建置選項:")
    print("1. Android (使用 Buildozer)")
    print("2. iOS 建置指引")
    print("3. 只建立橋接器和配置")

    try:
        choice = input("\n請輸入選擇 (1-3): ").strip()
    except KeyboardInterrupt:
        print("\n取消操作")
        return False

    if choice == "1":
        # 設定環境
        if not setup_kivy_environment():
            return False

        # 建立 Buildozer 配置
        create_buildozer_spec()

        # 建置 Android
        return build_android()

    elif choice == "2":
        # 顯示 iOS 建置指引
        return build_ios_simple()

    elif choice == "3":
        print("\n✅ 橋接器和配置已建立")
        print(f"   目錄: {MOBILE_DIR}")
        return True

    else:
        print("❌ 無效的選擇")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)