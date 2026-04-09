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


def check_dependencies():
    """檢查依賴"""
    try:
        import tkinter
        import pandas
        import pyttsx3
        import requests
        import openpyxl
        return True
    except ImportError as e:
        print(f"缺少依賴庫: {e}")
        print("請安裝所需的依賴庫：")
        print("pip install pandas pyttsx3 requests openpyxl")
        return False

def main():
    """主函數"""
    # 檢查依賴
    if not check_dependencies():
        sys.exit(1)
    
    # 設置日誌
    setup_logging()
    logger = logging.getLogger("Wofa_Runner")
    
    try:
        logger.info("啟動 Wofa_Runner 應用程式 main")
        
        # 導入應用程式
        from app import WofaRunnerApp
        
        # 創建並運行應用程式
        app = WofaRunnerApp()
        app.run()
        
    except KeyboardInterrupt:
        logger.info("收到中斷信號，程式正常退出")
    except Exception as e:
        logger.error(f"應用程式啟動失敗 main: {str(e)}")
        
        # 顯示錯誤對話框
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