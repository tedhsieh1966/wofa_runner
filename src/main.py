#!/usr/bin/env python3
"""
SmartPal - 具有長期記憶功能的 LLM 前端程式
主程式入口點
"""
#import readline
#print(f"readline is from{readline.__file__}")

import sys
import os

os.environ["PYTHONIOENCODING"] = "utf-8"
import logging
from pathlib import Path

# 添加模組路徑
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def setup_logging():
    """設置日誌系統"""
    # 建議使用絕對路徑，避免 PyInstaller 臨時目錄混淆
    if hasattr(sys, '_MEIPASS'):
        # 打包後的路徑處理
        base_dir = Path(sys.executable).parent
    else:
        base_dir = current_dir.parent

    log_dir = base_dir / "logs"
    log_dir.mkdir(exist_ok=True)

    handlers = []

    # 1. 檔案日誌 (最穩定)
    handlers.append(logging.FileHandler(log_dir / "wofa_runner.log", encoding='utf-8'))

    # 2. 控制台日誌 (僅在有 stdout 時加入)
    if sys.stdout is not None:
        try:
            # 強制 Windows 控制台支援 UTF-8
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            handlers.append(logging.StreamHandler(sys.stdout))
        except Exception:
            pass

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    logging.info("日誌系統初始化完成")

    # 設置第三方庫的日誌級別
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('speech_recognition').setLevel(logging.WARNING)


def check_dependencies(cli_mode: bool = False):
    """檢查依賴"""
    try:
        if not cli_mode:
            import tkinter
        import pandas
        import requests
        import openpyxl
        if not cli_mode:
            import pyttsx3
        return True
    except ImportError as e:
        print(f"缺少依賴庫: {e}")
        print("請安裝所需的依賴庫：")
        print("pip install pandas pyttsx3 requests openpyxl")
        return False


def _parse_cli_flag(argv):
    """從 argv 中找出 -cli 旗標。

    支援的形式（皆相容於現有的 sys.argv[1] = .wfa 路徑慣例）：
        wofa_runner -cli xxx.wfa
        wofa_runner xxx.wfa -cli
        wofa_runner --cli xxx.wfa
    回傳 (cli_mode, new_argv)。new_argv 已移除 -cli 旗標。
    """
    cli_mode = False
    new_argv = [argv[0]]
    for arg in argv[1:]:
        if arg in ("-cli", "--cli"):
            cli_mode = True
        else:
            new_argv.append(arg)
    return cli_mode, new_argv


def main():
    """主函數"""
    cli_mode, new_argv = _parse_cli_flag(sys.argv)
    sys.argv = new_argv

    if not check_dependencies(cli_mode=cli_mode):
        sys.exit(1)

    setup_logging()
    logger = logging.getLogger("Wofa_Runner")

    try:
        if cli_mode:
            logger.info("啟動 Wofa_Runner CLI 模式")
            from cli_app import WofaRunnerCliApp

            if len(sys.argv) < 2:
                print("用法: wofa_runner -cli <path/to/file.wfa>", file=sys.stderr)
                sys.exit(2)

            app = WofaRunnerCliApp()
            sys.exit(app.run())

        logger.info("啟動 Wofa_Runner 應用程式 main")
        from app import WofaRunnerApp

        app = WofaRunnerApp()
        app.run()

    except KeyboardInterrupt:
        logger.info("收到中斷信號，程式正常退出")
    except Exception as e:
        logger.error(f"應用程式啟動失敗 main: {str(e)}")

        if cli_mode:
            print(f"應用程式啟動失敗：{str(e)}", file=sys.stderr)
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror(
                    "WofaRunner 啟動錯誤",
                    f"應用程式啟動失敗：{str(e)}\n\n請檢查日誌文件獲取詳細信息。"
                )
                root.destroy()
            except:
                pass

        sys.exit(1)

if __name__ == "__main__":
    main()