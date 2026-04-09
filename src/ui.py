"""
WofaRunner 使用者介面模組
基於 tkinter 的現代化 UI 實現
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
from typing import Dict, Any, Optional


from py_libraries.UiOp import *
from py_libraries.LanguageOp import LanguageTranslator
from py_libraries.StreamingTextview import StreamingTextview


class WofaRunnerUI:

    def __init__(self, root, translator: LanguageTranslator):
        import platform

        # 檢測操作系統
        system = platform.system()

        # 定義各平台字體
        if system == "Darwin":  # macOS
            self.ui_font = "Helvetica"
            self.mono_font = "Menlo"
            self.ui_font_size = 15
        elif system == "Windows":  # Windows
            self.ui_font = "Microsoft YaHei"
            self.mono_font = "Consolas"
            self.ui_font_size = 11
        else:  # Linux 和其他系統
            self.ui_font = "DejaVu Sans"
            self.mono_font = "DejaVu Sans Mono"
            self.ui_font_size = 11

        self.node_waiting_user_input = None
        self.root = root

        self.voice_callback = None
        self.pending_user_input_callback = None

        self.translator: LanguageTranslator = translator
        self.logger = logging.getLogger("WofaRunner.UI")
        self.dialogs_display = None
        self.setup_ui()

    def setup_ui(self):
        """設置使用者介面"""
        self.root.title(self.translator.translate("app_name"))
        # self.root.geometry("1200x800")
        self.setup_styles()

        # 主佈局 - 必須先將 main_frame 放置到 root 中
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(
            fill=tk.BOTH, expand=True, padx=10, pady=10
        )  # 取消註解這行

        # 配置 grid 權重
        self.main_frame.grid_columnconfigure(0, weight=1)  # 只有聊天區域會擴展
        self.main_frame.grid_rowconfigure(0, weight=1)  # 重要：讓所有行都能擴展

        # 創建主聊天區域
        self.setup_dialogs()

        self.logger.info("UI 初始化完成")

    def setup_styles(self):
        """設置樣式"""
        style = ttk.Style()

        # 配置主題
        style.theme_use("clam")

        # 自定義樣式
        style.configure("Primary.TButton", padding=(10, 5))
        style.configure("Chat.TFrame", background="#f5f5f5")
        style.configure("User.TLabel", background="#e3f2fd", padding=(10, 5))
        style.configure("Assistant.TLabel", background="#f3e5f5", padding=(10, 5))

    def update_clock(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 更新標籤文字
        self.title_label.config(text=now)

        # 關鍵：1000 毫秒 (1秒) 後再次呼叫自己
        # 注意：這裡傳遞的是函數名稱 self.update_clock，不要加括號 ()
        self.title_label.after(1000, self.update_clock)

    def setup_dialogs(self):
        self.logger.debug("setup_dialogs")
        """設置聊天顯示區域 - 使用 ConversationDisplay"""
        self.dialogs_frame = ttk.Frame(self.main_frame)
        self.dialogs_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))

        # Header frame: WFA name | language | clock
        header_frame = ttk.Frame(self.dialogs_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        self.wfa_name_label = ttk.Label(
            header_frame, text="", font=(self.ui_font, self.ui_font_size, "bold")
        )
        self.wfa_name_label.pack(side=tk.LEFT)

        self.title_label = ttk.Label(
            header_frame, text="", font=(self.ui_font, self.ui_font_size)
        )
        self.title_label.pack(side=tk.RIGHT)

        self.lang_label = ttk.Label(
            header_frame,
            text=self.translator.current_language or "",
            font=(self.ui_font, self.ui_font_size),
        )
        self.lang_label.pack(side=tk.RIGHT, padx=(0, 15))

        self.update_clock()

        # 使用 StreamingTextview
        self.dialogs_display = StreamingTextview(
            self.dialogs_frame, width=60, height=20
        )
        self.dialogs_display.pack(fill="both", expand=True)

        self._prepare_dialog_styles()
        self.setup_dialog_input_area()

    def _prepare_dialog_styles(self):
        """配置樣式 - 符合實際使用"""
        self.logger.debug("_prepare_dialog_styles")
        # 用戶消息：靠右，淺色背景框，寬度80%，自動調整
        self.dialogs_display.add_custom_style(
            "user_message",
            {
                "background": "#F0F8FF",  # 淺藍色背景
                "foreground": "black",
                #'relief': 'solid',
                #'borderwidth': 1,
                "font": (self.ui_font, self.ui_font_size),
                "relief": "flat",
                "borderwidth": 0,
                "border": 1,
                "lmargin1": 100,  # 左邊距，讓消息靠右
                "lmargin2": 100,
                "rmargin": 20,
                "spacing1": 8,
                "spacing3": 5,
                "justify": "right",
                "wrap": "word",
            },
        )

        # 助手消息：置中，無背景色，佔據整個寬度
        self.dialogs_display.add_custom_style(
            "ai_message",
            {
                "background": "white",  # 無背景色
                "foreground": "blue",
                "relief": "flat",  # 無邊框
                "font": (self.ui_font, self.ui_font_size),
                "borderwidth": 0,
                "lmargin1": 20,
                "lmargin2": 20,
                "rmargin": 20,
                "spacing1": 8,
                "spacing3": 5,
                "justify": "left",  # 但文字靠左對齊（常見）
                "wrap": "word",
            },
        )

        # 助手消息：置中，無背景色，佔據整個寬度
        self.dialogs_display.add_custom_style(
            "std_output",
            {
                "background": "white",  # 無背景色
                "foreground": "black",
                "relief": "flat",  # 無邊框
                "font": (self.ui_font, self.ui_font_size),
                "borderwidth": 0,
                "lmargin1": 20,
                "lmargin2": 20,
                "rmargin": 20,
                "spacing1": 8,
                "spacing3": 5,
                "justify": "left",  # 但文字靠左對齊（常見）
                "wrap": "word",
            },
        )

        # 標題樣式（用於顯示對話標題）
        self.dialogs_display.add_custom_style(
            "dialog_title",
            {
                "font": (self.ui_font, self.ui_font_size + 1, "bold"),
                "foreground": "#2c3e50",
                "background": "white",
                "spacing1": 10,
                "spacing3": 5,
                "justify": "center",
            },
        )

    def add_custom_style(self, style_name, style):
        self.dialogs_display.add_custom_style(style_name=style_name, style=style)

    def display_dialog_message(self, message: Dict[str, Any]):
        """添加單條消息"""
        role = message.get("role", "")
        content = message.get("content", "")
        timestamp = message.get("timestamp", "")

        if role == "user":
            self.display_user_message(
                f"[{timestamp[0:10]} {timestamp[11:16]}] {content}", timestamp
            )
        elif role == "ai":
            self.display_ai_message(content, False, timestamp)

    def display_user_message(self, content: str, timestamp: str = ""):
        self.dialogs_display.display_text(
            is_streaming=False,
            text=content,
            style_name="user_message",
            is_markdown=False,
            is_typewriter=False,
        )
        self.dialogs_display.append_text("\n", "default", True)

    def on_waiting_user_input(self, prompt, node):
        self.node_waiting_user_input = node
        timestamp = datetime.now()
        if prompt:
            self.root.after(0, self.display_ai_message, prompt, False, timestamp)

    def start_ai_streaming(self):
        self.dialogs_display.start_streaming()

    def complete_ai_streaming(self):
        self.dialogs_display.finish_streaming()

    def display_ai_message(self, content: str, is_streaming=False, timestamp: str = ""):
        self.dialogs_display.display_text(
            is_streaming=is_streaming,
            text=content,
            style_name="ai_message",
            is_markdown=True,
            is_typewriter=is_streaming,
        )
        if not is_streaming:
            self.dialogs_display.append_text("\n\n", "default")

    def display_std_output(
        self,
        content: str,
        style_name="std_output",
        is_markdown=False,
        is_typewriter=False,
        is_streaming=False,
        timestamp: str = "",
    ):
        self.dialogs_display.display_text(
            is_streaming=is_streaming,
            text=content,
            style_name=style_name,
            is_markdown=is_markdown,
            is_typewriter=is_typewriter,
        )
        if not is_streaming:
            self.dialogs_display.append_text("\n\n", "default")

    def clear_display(self, timestamp_str: Optional[str] = None):
        """清空顯示"""
        self.dialogs_display.clear()

    # def setup_dialog_input_area(self):
    #    print("setup_dialog_input_area")
    #    """設置輸入區域"""
    #    self.input_frame = ttk.Frame(self.dialogs_frame)
    #    self.input_frame.pack(fill=tk.X, padx=5, pady=5)  # 添加一些內邊距
    #
    #    # 按鈕框架
    #    self.button_frame = ttk.Frame(self.input_frame)
    #    self.button_frame.pack(fill=tk.X, pady=5)
    #
    #    # 語音輸入按鈕
    #    self.voice_btn = ttk.Button(
    #        self.button_frame,
    #        text="🎤 "+ self.translator.translate("voice_input"),
    #        command=self._on_voice_input,
    #        width=10
    #    )
    #    self.voice_btn.pack(side=tk.LEFT, padx=(0, 5))
    #
    #
    #    # 輸入框框架 - 使用 grid 佈局來更好地控制比例
    #    dialog_input_frame = ttk.Frame(self.input_frame)
    #    dialog_input_frame.pack(fill=tk.BOTH, expand=True)  # 修改為 BOTH 和 expand
    #
    #    # 配置 grid 權重
    #    dialog_input_frame.grid_columnconfigure(0, weight=1)  # 輸入框佔大部分空間
    #    dialog_input_frame.grid_columnconfigure(1, weight=0)  # 按鈕固定寬度
    #    dialog_input_frame.grid_rowconfigure(0, weight=1)  # 行可擴展
    #
    #
    #    # 輸入框
    #    self.dialog_input = tk.Text(
    #        dialog_input_frame,
    #        height=3,
    #        font=(self.ui_font, self.ui_font_size),
    #        wrap=tk.WORD,
    #        background='white',  # 強制白底
    #        foreground='black',  # 強制黑字
    #        relief=tk.SOLID,
    #        borderwidth=1
    #    )
    #    self.dialog_input.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    #
    #    # 發送按鈕
    #    self.send_user_message_btn = ttk.Button(
    #        dialog_input_frame,
    #        text= self.translator.translate("send"),
    #        command=self._on_send_user_prompt,
    #        width=8
    #    )
    #    self.send_user_message_btn.grid(row=0, column=1, sticky="ns")
    #
    #    # 綁定回車鍵（但不包括 Shift+Enter）
    #    self.dialog_input.bind('<Return>', self._on_dialog_input_enter_pressed)
    #    self.dialog_input.bind('<Shift-Return>', self._on_dialog_input_shift_enter_pressed)

    def setup_dialog_input_area(self):
        """設置輸入區域"""
        self.input_frame = ttk.Frame(self.dialogs_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)

        # 輸入框框架
        dialog_input_frame = ttk.Frame(self.input_frame)
        dialog_input_frame.pack(fill=tk.BOTH, expand=True)

        # 配置 grid 權重
        dialog_input_frame.grid_columnconfigure(0, weight=1)  # 輸入框佔大部分空間
        dialog_input_frame.grid_columnconfigure(1, weight=0)  # 按鈕固定寬度
        dialog_input_frame.grid_rowconfigure(0, weight=1)
        dialog_input_frame.grid_rowconfigure(1, weight=1)

        # 輸入框 - 跨兩行
        self.dialog_input = tk.Text(
            dialog_input_frame,
            font=(self.ui_font, self.ui_font_size),
            wrap=tk.WORD,
            background="white",
            foreground="black",
            relief=tk.SOLID,
            borderwidth=1,
        )
        self.dialog_input.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 5))

        # 語音輸入按鈕 - 上方
        self.voice_btn = ttk.Button(
            dialog_input_frame,
            text="🎤 " + self.translator.translate("voice_input"),
            command=self._on_voice_input,
            width=10,
        )
        self.voice_btn.grid(row=0, column=1, sticky="nsew", pady=(0, 2))

        # 發送按鈕 - 下方
        self.send_user_message_btn = ttk.Button(
            dialog_input_frame,
            text=self.translator.translate("send"),
            command=self._on_send_user_prompt,
            width=10,
        )
        self.send_user_message_btn.grid(row=1, column=1, sticky="nsew", pady=(2, 0))

        # 綁定回車鍵
        self.dialog_input.bind("<Return>", self._on_dialog_input_enter_pressed)
        self.dialog_input.bind(
            "<Shift-Return>", self._on_dialog_input_shift_enter_pressed
        )

    def append_to_dialog_input(
        self, text: str, add_newline: bool = False, focus: bool = True
    ):
        """
        將文字附加到輸入框

        Args:
            text: 要附加的文字
            add_newline: 是否在附加前添加換行符
            focus: 是否將焦點設置到輸入框
        """
        try:
            if not hasattr(self, "dialog_input") or self.dialog_input is None:
                self.logger.warning("輸入框未初始化，無法附加文字")
                return False

            # 確保在主線程中操作
            if self.root:
                self.root.after(0, self._safe_append_to_input, text, add_newline, focus)
            else:
                self._safe_append_to_input(text, add_newline, focus)

            return True

        except Exception as e:
            self.logger.error(f"附加文字到輸入框時出錯: {e}")
            return False

    def _safe_append_to_input(
        self, text: str, add_newline: bool = False, focus: bool = True
    ):
        """安全地在主線程中附加文字到輸入框"""
        try:
            # 檢查輸入框是否存在且未銷毀
            if not self.dialog_input or not self.dialog_input.winfo_exists():
                self.logger.warning("輸入框不存在或已銷毀")
                return

            # 獲取當前文字並移除末尾的換行符
            current_text = self.dialog_input.get("1.0", tk.END).strip()

            # 構建新文字
            if current_text:
                if add_newline:
                    new_text = f"{current_text}\n{text}"
                else:
                    new_text = f"{current_text} {text}"
            else:
                new_text = text

            # 更新輸入框
            self.dialog_input.delete("1.0", tk.END)
            self.dialog_input.insert("1.0", new_text)

            # 滾動到底部
            self.dialog_input.see(tk.END)

            # 設置焦點
            if focus:
                self.dialog_input.focus_set()

            self.logger.debug(f"已附加 {len(text)} 個字符到輸入框")

        except Exception as e:
            self.logger.error(f"安全附加文字時出錯: {e}")

    def clear_dialog_input(self, keep_placeholder: bool = False):
        """清空輸入框

        Args:
            keep_placeholder: 是否保留預留位置文字
        """
        try:
            if not hasattr(self, "input_entry") or self.dialog_input is None:
                return False

            self.dialog_input.delete("1.0", tk.END)

            if keep_placeholder and hasattr(self, "_placeholder_text"):
                self.dialog_input.insert("1.0", self._placeholder_text)
                self.dialog_input.config(foreground="gray")

            return True

        except Exception as e:
            self.logger.error(f"清空輸入框時出錯: {e}")
            return False

    def get_dialog_input_text(self, strip: bool = True):
        """獲取輸入框文字

        Args:
            strip: 是否去除空白字符

        Returns:
            輸入框中的文字，如果輸入框不存在則返回空字串
        """
        try:
            if not hasattr(self, "input_entry") or self.dialog_input is None:
                return ""

            text = self.dialog_input.get("1.0", tk.END)
            if strip:
                return text.strip()
            return text

        except Exception as e:
            self.logger.error(f"獲取輸入框文字時出錯: {e}")
            return ""

    def set_wfa_name(self, name: str):
        """顯示目前執行的 WFA 名稱"""
        self.wfa_name_label.config(text=name)

    def set_callbacks(self, voice_callback, pending_user_input_callback):
        """設置回調函數"""

        self.voice_callback = voice_callback
        self.pending_user_input_callback = pending_user_input_callback

    def cleanup(self):
        """清理資源"""
        if hasattr(self, "dialogs_display"):
            self.dialogs_display.cleanup()

    def reset(self):
        if hasattr(self, "dialogs_display"):
            self.dialogs_display.reset()

    # 事件處理
    def _on_send_user_prompt(self):
        """發送消息"""
        user_prompt = self.dialog_input.get("1.0", tk.END).strip()
        if user_prompt:
            self.dialog_input.delete("1.0", tk.END)
        if self.node_waiting_user_input:
            self.node_waiting_user_input.on_user_input_received(user_prompt)
            self.node_waiting_user_input = None
        else:
            self.pending_user_input_callback(user_prompt)
        self.display_user_message(user_prompt, datetime.now())

    def _on_voice_input(self):
        """語音輸入"""
        if self.voice_callback:
            self.voice_callback()

    def _on_dialog_input_enter_pressed(self, event):
        """回車鍵處理"""
        if not event.state & 0x1:  # 沒有按住 Shift
            self._on_send_user_prompt()
            return "break"  # 阻止默認行為
        return None

    def _on_dialog_input_shift_enter_pressed(self, event):
        """Shift+Enter 處理 - 換行"""
        return None  # 允許默認行為（換行）

    def show_error(self, title: str, message: str):
        """顯示錯誤對話框"""
        messagebox.showerror(title, message)

    def show_info(self, title: str, message: str):
        """顯示信息對話框"""
        messagebox.showinfo(title, message)

    def show_warning(self, title: str, message: str):
        """顯示警告對話框"""
        messagebox.showwarning(title, message)
