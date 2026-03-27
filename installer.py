# installer.py
import os
import sys
import shutil
import ctypes
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
import sys
import os
import win32com
import win32com.client  # Should not raise errors

# 获取当前脚本所在目录（install/），然后定位父目录（根目录）
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)

# 将根目录添加到模块搜索路径
sys.path.insert(0, root_dir)
from app_info import *


class APP_Installer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_EXE + "安装程序")
        self.root.geometry("500x450")
        self.root.resizable(False, False)

        # 设置图标
        try:
            self.root.iconbitmap(sys._MEIPASS + '\\installer.ico')
        except:
            pass

        # 检查是否已安装
        self.is_installed = self.check_installation()

        self.create_widgets()

    def check_installation(self):
        """检查是否已安装"""
        appdata_dir = Path(os.getenv('APPDATA'))
        install_dir = appdata_dir / APP
        return install_dir.exists() and (install_dir / APP_EXE).exists()

    def create_widgets(self):
        # 标题
        title_frame = tk.Frame(self.root)
        title_frame.pack(pady=20)

        tk.Label(title_frame, text=BRIEF, font=("Arial", 16, "bold")).pack()
        tk.Label(title_frame, text=DESCRIPTION).pack(pady=5)

        # 显示安装状态
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=5)

        if self.is_installed:
            status_text = f"{APP} 已安装"
            status_color = "green"
        else:
            status_text = f"{APP} 未安装"
            status_color = "red"

        tk.Label(status_frame, text=status_text, fg=status_color, font=("Arial", 10, "bold")).pack()

        # 安装选项
        options_frame = tk.LabelFrame(self.root, text="安装選项", padx=10, pady=10)
        options_frame.pack(fill="x", padx=20, pady=10)

        self.create_shortcut_var = tk.BooleanVar(value=True)
        self.launch_after_install_var = tk.BooleanVar(value=True)

        tk.Checkbutton(options_frame, text="建立桌面圖標",
                       variable=self.create_shortcut_var).pack(anchor="w", pady=5)
        tk.Checkbutton(options_frame, text="安装完成后启动程序",
                       variable=self.launch_after_install_var).pack(anchor="w", pady=5)

        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(fill="x", padx=20, pady=10)

        self.progress = ttk.Progressbar(progress_frame, orient="horizontal",
                                        length=460, mode="determinate")
        self.progress.pack()

        # 按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        if self.is_installed:
            # 如果已安装，显示卸载按钮
            tk.Button(button_frame, text="卸载", width=10, command=self.uninstall, bg="red", fg="white").pack(
                side="left", padx=5)
            tk.Button(button_frame, text="重新安装", width=10, command=self.install).pack(side="left", padx=5)
        else:
            # 如果未安装，显示安装按钮
            tk.Button(button_frame, text="安裝", width=10, command=self.install).pack(side="left", padx=5)

        tk.Button(button_frame, text="退出", width=10, command=self.root.destroy).pack(side="right", padx=5)

    def is_admin(self):
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def request_admin(self):
        """请求管理员权限"""
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

    def uninstall(self):
        """执行卸载过程"""
        try:
            # 删除安装目录
            appdata_dir = Path(os.getenv('APPDATA'))
            install_dir = appdata_dir / APP
            if install_dir.exists():
                shutil.rmtree(install_dir)

            # 删除启动项
            startup_dir = Path(os.getenv('APPDATA')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            shortcut_path = startup_dir / APP + ".lnk"
            if shortcut_path.exists():
                os.remove(shortcut_path)

            # 删除桌面快捷方式
            desktop = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))
            desktop_shortcut = desktop / APP_DESKTOP + ".lnk"
            if desktop_shortcut.exists():
                os.remove(desktop_shortcut)

            messagebox.showinfo("卸载完成", APP + "已成功卸载")
            self.is_installed = False
            # 重新创建界面以更新状态
            for widget in self.root.winfo_children():
                widget.destroy()
            self.create_widgets()

        except Exception as e:
            messagebox.showerror("卸载错误", f"卸载过程中发生错误:\n{str(e)}")

    def install(self):
        """执行安装过程"""
        try:
            # 确定安装目录
            appdata_dir = Path(os.getenv('APPDATA'))
            install_dir = appdata_dir / APP

            # --- 修改 1: 保護 config.json，不要直接 rmtree ---
            if install_dir.exists():
                # 遍歷資料夾內容進行刪除，但避開 config.json 和 data
                for item in install_dir.iterdir():
                    if item.name == "config.json":
                        continue  # 跳過，不刪除設定檔
                    if item.is_dir():
                        if item.name != "data":
                            shutil.rmtree(item)
                    else:
                        item.unlink()
            else:
                install_dir.mkdir(parents=True, exist_ok=True)

            self.progress["value"] = 20

            # 复制文件
            source_dir = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).parent

            # 複製所有必要的文件
            files_to_copy = [
                (source_dir / APP_EXE, install_dir / APP_EXE),  # 主程式
                (source_dir / LANGUAGES, install_dir / LANGUAGES),  # 語言文件
                (source_dir / APP_ICON, install_dir / APP_ICON),  # 圖標
            ]

            for source, target in files_to_copy:
                if source.exists():
                    shutil.copy2(source, target)
                    print(f"已複製: {source.name}")
                else:
                    print(f"警告: 找不到文件 {source.name}")

            # --- 修改 3: 專門處理 wofa 資料夾的複製 ---
            source_wofa = source_dir / "wofa"
            target_wofa = install_dir / "wofa"

            if source_wofa.exists():
                # 如果目標資料夾已存在，先刪除舊的再複製新的
                if target_wofa.exists():
                    shutil.rmtree(target_wofa)
                shutil.copytree(source_wofa, target_wofa)
                print("已複製 wofa 資料夾")

            self.progress["value"] = 60

            # 创建桌面快捷方式
            if self.create_shortcut_var.get():
                desktop = Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))
                shortcut_path = desktop / APP_DESKTOP_LINK

                shell = win32com.client.Dispatch("WScript.Shell")
                shortcut = shell.CreateShortCut(str(shortcut_path))
                shortcut.TargetPath = str(install_dir / APP_EXE)
                shortcut.WorkingDirectory = str(install_dir)
                shortcut.IconLocation = str(install_dir / APP_ICON)
                shortcut.Save()

            self.progress["value"] = 80

            self.progress["value"] = 100
            messagebox.showinfo("安装完成", APP + "已成功安装！")

            # 安装后启动程序
            if self.launch_after_install_var.get():
                os.startfile(str(install_dir / APP_EXE))

            self.is_installed = True
            # 重新创建界面以更新状态
            for widget in self.root.winfo_children():
                widget.destroy()
            self.create_widgets()

        except Exception as e:
            messagebox.showerror("安装错误", f"安装过程中发生错误:\n{str(e)}")
            self.progress["value"] = 0


if __name__ == "__main__":
    app = APP_Installer()
    app.root.mainloop()