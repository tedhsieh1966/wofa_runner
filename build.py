# build.py
import os
import platform
import PyInstaller.__main__
import shutil
import subprocess
import glob
from app_info import *


def create_dmg_mac():
    """為 macOS 建立 DMG 檔案"""
    print("開始建立 macOS DMG 檔案...")

    app_path = f"{DIR_DIST}/{APP_NAME}.app"
    dmg_name = f"{APP_NAME}.dmg"
    temp_dmg = f"temp_{dmg_name}"

    if not os.path.exists(app_path):
        print(f"❌ 錯誤: 找不到應用程式 {app_path}")
        return False

    try:
        # 刪除舊的 DMG 檔案
        if os.path.exists(dmg_name):
            os.remove(dmg_name)

        # 建立 DMG
        cmd = [
            'hdiutil', 'create',
            '-volname', APP_NAME,
            '-srcfolder', app_path,
            '-ov', dmg_name,
            '-format', 'UDZO'
        ]

        subprocess.run(cmd, check=True)
        print(f"✅ DMG 檔案建立完成: {dmg_name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ 建立 DMG 失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        return False


def create_appimage_linux():
    """為 Linux 建立 AppImage (需要安裝 appimagetool)"""
    print("開始建立 Linux AppImage...")

    # 檢查是否安裝了 appimagetool
    try:
        subprocess.run(['which', 'appimagetool'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("⚠️  警告: 未找到 appimagetool，跳過 AppImage 建立")
        print("請安裝 appimagetool: https://github.com/AppImage/AppImageKit")
        return False

    # 建立 AppImage 所需目錄結構
    app_dir = f"{APP_NAME}.AppDir"
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)

    os.makedirs(app_dir, exist_ok=True)

    # 複製可執行檔
    executable_path = f"{DIR_DIST}/{APP_NAME}"
    if os.path.exists(executable_path):
        shutil.copy(executable_path, f"{app_dir}/{APP_NAME}")
        os.chmod(f"{app_dir}/{APP_NAME}", 0o755)  # 設定執行權限

    # 建立 desktop 檔案
    desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment={DESCRIPTION}
Exec={APP_NAME}
Icon={APP_NAME}
Terminal=false
Type=Application
Categories=Utility;
"""

    with open(f"{app_dir}/{APP_NAME}.desktop", 'w') as f:
        f.write(desktop_content)

    # 複製圖標
    if os.path.exists(FP_APP_ICON):
        shutil.copy(FP_APP_ICON, f"{app_dir}/{APP_NAME}.png")

    # 使用 appimagetool 建立 AppImage
    try:
        appimage_name = f"{APP_NAME}-x86_64.AppImage"
        cmd = ['appimagetool', app_dir, appimage_name]
        subprocess.run(cmd, check=True)
        print(f"✅ AppImage 建立完成: {appimage_name}")
        return True
    except Exception as e:
        print(f"❌ 建立 AppImage 失敗: {e}")
        return False
    finally:
        # 清理臨時目錄
        if os.path.exists(app_dir):
            shutil.rmtree(app_dir)


def build_app():
    try:
        # 檢查圖標文件是否存在
        icon_path = FP_APP_ICON
        if not os.path.exists(icon_path):
            print(f"⚠️ 警告：找不到圖標文件 {icon_path}")
            if platform.system() == 'Darwin':
                print("請確保有 .icns 格式的圖標文件")
            elif platform.system() == 'Linux':
                print("請確保有 .png 格式的圖標文件")

        # 清理之前的构建
        if os.path.exists(DIR_DIST):
            shutil.rmtree(DIR_DIST)
        if os.path.exists(DIR_BUILD):
            shutil.rmtree(DIR_BUILD)

        print(f"開始建置 {APP_NAME} 於 {platform.system()}...")
        print(f"使用圖標: {FP_APP_ICON}")

        # 建立構建命令
        build_args = [
            FP_APP_PY,
            '--onefile',
            '--windowed',
            '--hidden-import=langchain.chains.retrieval',
            '--hidden-import=langchain.chains.history_aware_retriever',
            '--hidden-import=pyttsx3',  # <--- 新增這一行
            '--hidden-import=pyttsx3.drivers',  # <--- 有時需要驅動
            '--hidden-import=pyttsx3.drivers.sapi5',  # <--- Windows 語音引擎
            f'--path={PY_LIBRARIES_PYD_DIR}.',
            f'--name={APP_NAME}',
            f'--icon={FP_APP_ICON}',
            f'--add-data={FP_LANGUAGES}{SEPARATOR}.',
            f'--add-data={FP_WORKFLOW_LANGUAGES}{SEPARATOR}.',
            f'--add-data={FP_APP_ICON}{SEPARATOR}.',
         #   f'--path={PY_LIBRARIES_PYD_DIR}',
         #   f'--path={PY_LLM_API_PYD_DIR}',
         #   f'--path={PY_WORKFLOW_PYD_DIR}',
         #   f'--path={WOFA_IDE_PYD_DIR}',
         #   f'--path={WOFA_SERVER_PYD_DIR}',
         #   f'--add-data={os.path.join(ROOT_DIR, "wofa")}{SEPARATOR}wofa',
            '--distpath=dist',
            '--workpath=build',
        ]

        # 找出所有符合的檔案
       # wfa_files = glob.glob(os.path.join(ROOT_DIR, "wofa", "*.wfa"))
        # 為每個檔案生成 --add-data 參數
        #for f in wfa_files:
        #    # 這裡將檔案放在打包後的根目錄（.），或指定子目錄
        #    build_args.append(f'--add-data={f}{SEPARATOR}.')

        # 平台特定調整
        system = platform.system()
        if system == 'Linux':
            # Linux 可能需要額外的隱藏匯入
            build_args.extend([
                '--hidden-import=xcb',
                '--hidden-import=PyQt5.QtX11Extras',
            ])
        elif system == 'Darwin':
            # macOS 特定設定
            build_args.extend([
                '--hidden-import=PyQt5.QtMacExtras',
                '--osx-bundle-identifier=com.example.smartpal',
            ])

        # 執行構建
        PyInstaller.__main__.run(build_args)

        # 複製配置文件（如果有）
       # config_files = ['config.json', 'settings.ini']
       # for config_file in config_files:
       #     if os.path.exists(config_file):
       #         shutil.copy(config_file, DIR_DIST)
       #         print(f"已複製配置檔案: {config_file}")

        print(f"✅ 建置完成！可執行檔 {APP_EXE} 在 {DIR_DIST} 目錄中")

        # 平台特定後處理
        if system == 'Darwin':
            # macOS: 建立 DMG
            create_dmg_mac()
        elif system == 'Linux':
            # Linux: 建立 AppImage
            create_appimage_linux()

        return True

    except Exception as e:
        print(f"❌ 建置過程中發生錯誤:\n{str(e)}")
        return False


if __name__ == '__main__':
    success = build_app()
    exit(0 if success else 1)