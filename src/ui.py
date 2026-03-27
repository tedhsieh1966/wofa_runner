"""
SmartPal 使用者介面模組
基於 tkinter 的現代化 UI 實現
"""

import logging
import tkinter

from py_libraries.UiOp import *
from py_libraries.ImageOp import resize_images
from py_libraries.LanguageOp import LanguageTranslator
from py_libraries.StreamingTextview import StreamingTextview
from py_libraries.ReadOnlyTk import ReadOnlyScrolledText
from py_llm_api.LLM_Cloud import LLMS_API

from modules.utils import get_resource_path
from config_manager import ConfigManager
from modules.history_manager import HistoryManager, Dialog
from wofa_ide.editors import Editor_LLMS_API



class SmartPalUI:
    """SmartPal 主使用者介面"""
    
    def __init__(self, root, translator:LanguageTranslator, memory_mgr, history_mgr, config_mgr=None):
        import platform

        # 檢測操作系統
        system = platform.system()

        # 定義各平台字體
        if system == 'Darwin':  # macOS
            self.ui_font = 'Helvetica'
            self.mono_font = 'Menlo'
            self.ui_font_size = 15
        elif system == 'Windows':  # Windows
            self.ui_font = 'Microsoft YaHei'
            self.mono_font = 'Consolas'
            self.ui_font_size = 11
        else:  # Linux 和其他系統
            self.ui_font = 'DejaVu Sans'
            self.mono_font = 'DejaVu Sans Mono'
            self.ui_font_size = 11

        self.root = root
        self.config_mgr : ConfigManager  = config_mgr
        self.translator: LanguageTranslator=translator
        self.logger = logging.getLogger("SmartPal.UI")
        self.memory_mgr = memory_mgr
        self.history_mgr =history_mgr
        self.current_history_dialog_id = None
        self.current_memory_dialog_id = None
        self.dialogs_display = None
        self.list_checkbox_llms = None
        self.password_frm = None
        self.password = None
        self.setup_ui()


    def setup_ui(self):
        """設置使用者介面"""
        self.root.title(self.translator.translate("app_name"))
        #self.root.geometry("1200x800")
        self.setup_styles()

        # 主佈局 - 必須先將 main_frame 放置到 root 中
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)  # 取消註解這行

        # 配置 grid 權重
        self.main_frame.grid_columnconfigure(1, weight=1)  # 只有聊天區域會擴展
        self.main_frame.grid_rowconfigure(0, weight=1)  # 重要：讓所有行都能擴展

        # 創建側邊欄
        self.setup_history()

        # 創建主聊天區域
        self.setup_dialogs()
        #self.setup_chat_area()

        # 創建伴侶對話框
        self.setup_memory()

        self.logger.info("UI 初始化完成")



    def setup_styles(self):
        """設置樣式"""
        style = ttk.Style()
        
        # 配置主題
        style.theme_use('clam')
        
        # 自定義樣式
        style.configure('Primary.TButton', padding=(10, 5))
        style.configure('Chat.TFrame', background='#f5f5f5')
        style.configure('User.TLabel', background='#e3f2fd', padding=(10, 5))
        style.configure('Assistant.TLabel', background='#f3e5f5', padding=(10, 5))

    def setup_history(self):
        print("setup_history");
        """設置側邊欄"""
        # 側邊欄框架
        self.history_frame = ttk.Frame(self.main_frame, width=250)
        self.history_frame.grid(row=0, column=0, sticky="nswe", padx=(0, 10))
        self.history_frame.pack_propagate(False)
        self.history_frame.grid_propagate(False)  # 重要：防止 grid 自動調整

        # --- 上半部分：對話歷史 (50% 高度) ---
        self.chat_history_container = ttk.LabelFrame(
            self.history_frame,
            text=self.translator.translate("dialog_history")
        )
        self.chat_history_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # 標題
        title_label = ttk.Label(
            self.chat_history_container,
            text=self.translator.translate("dialog_history"),
            font=("Microsoft YaHei", 12, "bold")
        )
        title_label.pack(pady=10)

        # 搜索框
        search_history_frame = ttk.Frame(self.chat_history_container)
        search_history_frame.pack(fill=tk.X, padx=10, pady=5)

        self.search_history = ttk.Entry(search_history_frame)
        self.search_history.pack(fill=tk.X)
        self.search_history.insert(0, self.translator.translate("search_dialog") + "...")
        self.search_history.bind('<FocusIn>', self._on_search_history_focus_in)
        self.search_history.bind('<FocusOut>', self._on_search_history_focus_out)
        self.search_history.bind('<KeyRelease>', self._on_search_history_key_release)

        # 對話列表
        list_frame = ttk.Frame(self.chat_history_container)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.history_listbox = tk.Listbox(
            list_frame,
            font=(self.ui_font, self.ui_font_size-1),
            selectmode=tk.SINGLE,
            exportselection=False,
            bg='white',
            fg="black",
            relief=tk.FLAT,
            height=20
        )

        # 添加滾動條
        list_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.history_listbox.config(yscrollcommand=list_scrollbar.set)
        list_scrollbar.config(command=self.history_listbox.yview)

        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.history_listbox.bind('<<ListboxSelect>>', self._on_historical_dialog_select)

        # 新對話按鈕
        new_chat_btn = ttk.Button(
            self.chat_history_container,
            text="+ "+self.translator.translate("new_dialog"),
          #  command=self._new_dialog,
            command=self.start_new_dialog,
            style='Primary.TButton'
        )
        new_chat_btn.pack(pady=10, padx=10, fill=tk.X)

        self.update_history_list()

        # --- 下半部分：待辦清單 (50% 高度) ---
        self.todo_container = ttk.LabelFrame(
            self.history_frame,
            text="待辦事項 (Todo List)"
        )
        self.todo_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        todo_list_frame = ttk.Frame(self.todo_container)
        todo_list_frame.pack(fill=tk.BOTH, expand=True)

        ## 使用 Treeview 顯示 名稱 + 下次執行時間
        ##columns = ("name", "next_time")
        #columns = ("name_next_time")
        #self.todo_tree = ttk.Treeview(
        #    todo_list_frame,
        #    columns=columns,
        #    show='headings',
        #    selectmode='browse'
        #)
#
        ## 定義表頭
        ##self.todo_tree.heading("name", text="名稱")
        ##self.todo_tree.heading("next_time", text="執行時間")
        #self.todo_tree.heading("name_next_time", text= self.translator.translate("name_next_time") )
#
        ## 定義欄位寬度
        ##self.todo_tree.column("name", width=100, anchor="w")
        ##self.todo_tree.column("next_time", width=100, anchor="center")
        #self.todo_tree.column("name_next_time", width=200, anchor="w")
#
        #todo_scrollbar = ttk.Scrollbar(todo_list_frame, orient=tk.VERTICAL, command=self.todo_tree.yview)
        #self.todo_tree.config(yscrollcommand=todo_scrollbar.set)
#
        #self.todo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        #todo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.todo_canvas = tk.Canvas(todo_list_frame, bg="white", highlightthickness=0)
        todo_scrollbar = ttk.Scrollbar(todo_list_frame, orient=tk.VERTICAL, command=self.todo_canvas.yview)

        # 承載內容的真正容器
        self.todo_scrollable_frame = tk.Frame(self.todo_canvas, bg="white")

        # 綁定捲動事件
        self.todo_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.todo_canvas.configure(scrollregion=self.todo_canvas.bbox("all"))
        )

        self.todo_canvas.create_window((0, 0), window=self.todo_scrollable_frame, anchor="nw", width=200)  # width 根據需求調整
        self.todo_canvas.configure(yscrollcommand=todo_scrollbar.set)

        self.todo_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        todo_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 初次載入數據
        self.load_todo_list()

    def update_history_list(self):
        """載入歷史對話到側邊欄"""
        try:
            # 清空列表
            self.history_listbox.delete(0, tk.END)

            # 從 History Manager 獲取對話（按時間倒序）
            dialogs = self.history_mgr.get_all_dialogs()

            for dialog in dialogs:
                updated_time = datetime.fromisoformat(dialog.updated_at).strftime("%m/%d %H:%M")
                title = f"{dialog.title}\n{updated_time}"
                self.history_listbox.insert(tk.END, title)

            self.logger.info(f"已載入 {len(dialogs)} 個歷史對話")

        except Exception as e:
            self.logger.error(f"載入歷史對話時出錯: {e}")

    def load_todo_list(self):
        """改用 Label 組合實現上下排版與不同字級"""
        # 1. 清空舊數據
        for widget in self.todo_scrollable_frame.winfo_children():
            widget.destroy()

        todo_dict = self.memory_mgr.get_todo_dict()
        if not todo_dict:
            return

        # 2. 填充數據
        for key in todo_dict:
            todo = todo_dict[key]
            name = todo.get("name", "未命名")
            next_time = todo.get("next_time", "無")

            # 每一個項目的容器
            item_frame = tk.Frame(self.todo_scrollable_frame, bg="white", pady=5)
            item_frame.pack(fill=tk.X, expand=True, padx=5)

            # 上層：名稱（正常大小）
            name_label = tk.Label(
                item_frame,
                text=name,
                font=("Microsoft JhengHei", 10, "bold"),
                bg="white", anchor="w"
            )
            name_label.pack(fill=tk.X)

            # 下層：時間（較小字體，顏色稍淡）
            time_label = tk.Label(
                item_frame,
                text=next_time,
                font=("Microsoft JhengHei", 8),
                fg="gray", bg="white", anchor="w"
            )
            time_label.pack(fill=tk.X)

            # 分隔線
            line = tk.Frame(self.todo_scrollable_frame, height=1, bg="#eeeeee")
            line.pack(fill=tk.X)
    #def _load_todo_list(self):
    #    """從 memory_mgr 獲取最新數據並刷新界面"""
    #    # 清空舊數據
    #    for item in self.todo_tree.get_children():
    #        self.todo_tree.delete(item)
#
    #    # 獲取資料
    #    # 注意：根據你的代碼，這裡假設 get_todo_dict() 返回 {"todo_list": [...]}
    #    todo_dict = self.memory_mgr.get_todo_dict()
    #    if todo_dict:
    #        # 填充數據
    #        for i, todo in enumerate(todo_dict):
    #            name = todo.get("name", "未命名")
    #            next_time = todo.get("next_time", "無")
#
    #            self.todo_tree.insert("", tk.END, values=(name, next_time))

    def update_clock(self):
        from datetime import datetime

        # 格式化時間 (包含時:分:秒)
        # 如果只要日期，可以維持 "%Y-%m-%d"
        # 如果要像時鐘，建議 "%Y-%m-%d %H:%M:%S"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 更新標籤文字
        self.title_label.config(text=now)

        # 關鍵：1000 毫秒 (1秒) 後再次呼叫自己
        # 注意：這裡傳遞的是函數名稱 self.update_clock，不要加括號 ()
        self.title_label.after(1000, self.update_clock)

    def setup_dialogs(self):
        print("setup_dialogs")
        """設置聊天顯示區域 - 使用 ConversationDisplay"""
        self.dialogs_frame = ttk.Frame(self.main_frame)
        self.dialogs_frame.grid(row=0, column=1, sticky="nswe", padx=(0, 10))

        self.title_label = ttk.Label(
            self.dialogs_frame,
            text="",
            font=("Microsoft YaHei", 14, "bold")
        )
        self.title_label.pack(anchor="w", pady=(0, 10))
        self.update_clock()

        # 使用 StreamingTextview
        self.dialogs_display = StreamingTextview(
            self.dialogs_frame,
            width=60,
            height=20
        )
        self.dialogs_display.pack(fill="both", expand=True)

        
        self._prepare_dialog_styles()
        self. setup_dialog_input_area()

    def _prepare_dialog_styles(self):
        """配置樣式 - 符合實際使用"""
        print("_prepare_dialog_styles")
        # 用戶消息：靠右，淺色背景框，寬度80%，自動調整
        self.dialogs_display.add_custom_style("user_message", {
            'background': '#F0F8FF',  # 淺藍色背景
            'foreground': 'black',
           #'relief': 'solid',
           #'borderwidth': 1,
            "font" : (self.ui_font, self.ui_font_size),
            'relief': 'flat',
            'borderwidth': 0,
            'border': 1,
            'lmargin1': 100,  # 左邊距，讓消息靠右
            'lmargin2': 100,
            'rmargin': 20,
            'spacing1': 8,
            'spacing3': 5,
            'justify': 'right',
            'wrap': 'word',
        })

        # 助手消息：置中，無背景色，佔據整個寬度
        self.dialogs_display.add_custom_style("ai_message", {
            'background': 'white',  # 無背景色
            'foreground': 'black',
            'relief': 'flat',  # 無邊框
            "font": (self.ui_font, self.ui_font_size),
            'borderwidth': 0,
            'lmargin1': 20,
            'lmargin2': 20,
            'rmargin': 20,
            'spacing1': 8,
            'spacing3': 5,
            'justify': 'left',  # 但文字靠左對齊（常見）
            'wrap': 'word'
        })

        # 標題樣式（用於顯示對話標題）
        self.dialogs_display.add_custom_style("dialog_title", {
            'font': (self.ui_font, self.ui_font_size+1, 'bold'),
            'foreground': '#2c3e50',
            'background': 'white',
            'spacing1': 10,
            'spacing3': 5,
            'justify': 'center'
        })

    def start_new_dialog(self):
        """開始新對話"""
        self.current_history_dialog_id = None
        self.dialogs_display.clear()
        self.history_listbox.select_clear(0, tk.END)
        self.memory_prompt_display.config(state=tk.NORMAL)
        self.memory_prompt_display.delete(1.0, tk.END)
        self.memory_prompt_display.config(state=tk.DISABLED)
        self.memory_reply_display.clear()
        self.current_memory_dialog_id = None

    def display_dialog(self, dialog: Dialog):
        """顯示對話集"""

        updated_time = datetime.fromisoformat(dialog.updated_at)
        self.clear_display(updated_time.strftime('%Y-%m-%d'))

        # 更新標題
        self.title_label.config(text=f"對話集: {dialog.title}")

        # 顯示所有消息
        for message in dialog.messages:
            self.display_dialog_message(message)

    def display_dialog_message(self, message: Dict[str, Any]):
        """添加單條消息"""
        role = message.get('role', '')
        content = message.get('content', '')
        timestamp = message.get('timestamp', '')

        if role == 'user':
            self.display_user_message(f"[{timestamp[0:10]} {timestamp[11:16]}] {content}", timestamp)
        elif role == 'ai':
            self.display_ai_message(content, False, timestamp)

    def display_user_message(self, content: str, timestamp: str = ""):

        self.dialogs_display.display_text(
            is_streaming=False,
            text=content,
            style_name="user_message",
            is_markdown=False,
            is_typewriter=False
        )
        self.dialogs_display.append_text("\n", "default", True)

    def start_ai_streaming(self):
        self.dialogs_display.start_streaming()

    def complete_ai_streaming(self):
        self.dialogs_display.finish_streaming()

    def display_ai_message(self, content: str, is_streaming= False, timestamp: str = ""):

        self.dialogs_display.display_text(
            is_streaming=is_streaming,
            text=content,
            style_name="ai_message",
            is_markdown=True,
            is_typewriter=is_streaming
        )
        if not is_streaming:
            self.dialogs_display.append_text("\n\n", "default")


    def clear_display(self, timestamp_str: Optional[str] = None):
        """清空顯示"""
        self.dialogs_display.clear()
        if not timestamp_str:
            timestamp_str = datetime.now().strftime("%Y-%m-%d")
        self.title_label.config(text=timestamp_str)


    def on_llm_api_key_changed(self, llm_api_key: str):
        self.config_mgr.set_current_llm_api_key(llm_api_key)

    def setup_dialog_input_area(self):
        print("setup_dialog_input_area")
        """設置輸入區域"""
        self.input_frame = ttk.Frame(self.dialogs_frame)
        self.input_frame.pack(fill=tk.X, padx=5, pady=5)  # 添加一些內邊距

        # 按鈕框架
        self.button_frame = ttk.Frame(self.input_frame)
        self.button_frame.pack(fill=tk.X, pady=5)

        # 語音輸入按鈕
        self.voice_btn = ttk.Button(
            self.button_frame,
            text="🎤 "+ self.translator.translate("voice_input"),
            command=self._on_voice_input,
            width=10
        )
        self.voice_btn.pack(side=tk.LEFT, padx=(0, 5))

        # 文件上傳按鈕
        self.file_btn = ttk.Button(
            self.button_frame,
            text="📎 "+ self.translator.translate("upload_files"),
            command=self._on_file_upload,
            width=10
        )
        self.file_btn.pack(side=tk.LEFT, padx=(0, 5))
        print("setup_dialog_input_area Combo_Text_Editor before")
        self.llm_selector = Combo_Text_Editor(parent=self.button_frame,
                          label=self.translator.translate("select_LLM"),
                          var=self.config_mgr.get_current_llm_api_key(),
                          combo_source=self.config_mgr.get_llms_api().get_list_key(),
                          is_nullable=True,
                          null_str=self.translator.translate("none"),
                          callback=self.on_llm_api_key_changed).pack( field_width=40, side=tk.LEFT, padx=(0, 5))
        print("setup_dialog_input_area Combo_Text_Editor after")

        is_multiple_llms = self.config_mgr.get_is_multiple_llms()
        self.checkbox_multiple_llms = CheckBox_Editor(
            self.button_frame,
            label= self.translator.translate("is_multiple_llms"),
            var=is_multiple_llms ,
            callback=self._on_select_multiple_llms,
        ).pack(side=tk.LEFT, padx=(0, 5))
        self.dialogs_frame.after(1, self._on_select_multiple_llms(is_multiple_llms))

        # 輸入框框架 - 使用 grid 佈局來更好地控制比例
        dialog_input_frame = ttk.Frame(self.input_frame)
        dialog_input_frame.pack(fill=tk.BOTH, expand=True)  # 修改為 BOTH 和 expand

        # 配置 grid 權重
        dialog_input_frame.grid_columnconfigure(0, weight=1)  # 輸入框佔大部分空間
        dialog_input_frame.grid_columnconfigure(1, weight=0)  # 按鈕固定寬度
        dialog_input_frame.grid_rowconfigure(0, weight=1)  # 行可擴展


        # 輸入框
        self.dialog_input = tk.Text(
            dialog_input_frame,
            height=3,
            font=(self.ui_font, self.ui_font_size),
            wrap=tk.WORD,
            background='white',  # 強制白底
            foreground='black',  # 強制黑字
            relief=tk.SOLID,
            borderwidth=1
        )
        self.dialog_input.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        # 發送按鈕
        self.send_user_message_btn = ttk.Button(
            dialog_input_frame,
            text= self.translator.translate("send"),
            command=self._on_send_user_prompt,
            width=8
        )
        self.send_user_message_btn.grid(row=0, column=1, sticky="ns")

        # 綁定回車鍵（但不包括 Shift+Enter）
        self.dialog_input.bind('<Return>', self._on_dialog_input_enter_pressed)
        self.dialog_input.bind('<Shift-Return>', self._on_dialog_input_shift_enter_pressed)

        #self._on_select_multiple_llms(is_multiple_llms)


    def _on_select_multiple_llms(self, is_multiple_llms:bool):
        try:
            # 載入當前 LLMS 配置
            if is_multiple_llms:
                self.config_mgr.set_is_multiple_llms(True)
                # 創建編輯器
                self._open_multiple_llm_selector()
            else:
                self.config_mgr.set_is_multiple_llms(False)
                if self.list_checkbox_llms and hasattr(self, 'multiple_llm_selector_top'):
                    self.multiple_llm_selector_top.withdraw()


            #width = editor.get_width()
            #height = editor.get_height()
            #root_x = self.select_multiple_llms.winfo_x()
            #root_y = self.select_multiple_llms.winfo_y()
            #root_width = self.select_multiple_llms.winfo_width()
#
            ## 計算位置：貼齊 root 右側
            #x = root_x
            #y = root_y - height -10
#
            ## 設置 top 的位置（保持自動計算的大小）
            #editor.geometry(f"+{x}+{y}")

        except Exception as e:
            print(f"開啟 多重 LLM 設定時出錯: {e}")
            self.logger.error(f"開啟 多重 LLM 設定時出錯: {e}")

    def _open_multiple_llm_selector(self):
        if hasattr(self, 'multiple_llm_selector_top') and self.multiple_llm_selector_top.winfo_exists():
            # 如果已經存在，直接取消隱藏並提到最前
            self.multiple_llm_selector_top.deiconify()
            self.multiple_llm_selector_top.lift()
            return

        llms_api = self.config_mgr.get_llms_api()
        current_list_llm_api_key = self.config_mgr.get_current_list_llm_api_key()
        self.multiple_llm_selector_top = tk.Toplevel(self.button_frame)
        self.multiple_llm_selector_top.overrideredirect(True)
        outer_frame = tk.Frame(self.multiple_llm_selector_top,
                               bg="#333333",  # 邊框顏色
                               highlightbackground="gray",
                               highlightthickness=1)
        outer_frame.pack(fill=tk.BOTH, expand=True)
        #self.multiple_llm_selector_top.minsize(200, 50)
        #self.multiple_llm_selector_top.title(self.translator.translate("multiple_llm"))
        #top.transient(self.button_frame)
        #top.grab_set()



        self.list_checkbox_llms = List_Checkbox_Editor(
            parent=outer_frame,
           # parent=self.multiple_llm_selector_top,
            callback=self._on_multiple_llms_updated,
            list_source=llms_api.get_list_key(),
            var=current_list_llm_api_key,
            is_use_index=False
        ).pack(fill=tk.BOTH, expand=True)

        outer_frame.update_idletasks()
        outer_frame.update()
        self.multiple_llm_selector_top.update_idletasks()
        self.multiple_llm_selector_top.update()
        #self.button_frame.update_idletasks()
        main_window = self.button_frame.winfo_toplevel()
        main_window.update_idletasks()
        # 3. 抓取按鈕框的大小 (用於偏移計算)
        frame_w = self.button_frame.winfo_width()
        frame_h = self.button_frame.winfo_height()
        # 獲取 top 的實際大小
        popup_width = self.multiple_llm_selector_top.winfo_width()
        popup_height = self.multiple_llm_selector_top.winfo_height()
        #        # 獲取 root 的位置
        #root_x = self.multiple_llm_selector_top.winfo_x()
        #root_y = self.multiple_llm_selector_top.winfo_y()
        root_x = self.checkbox_multiple_llms.winfo_rootx()
        root_y = self.checkbox_multiple_llms.winfo_rooty()
        root_width = self.checkbox_multiple_llms.winfo_width()
        #root_x = self.button_frame.winfo_rootx()
        #root_y = self.button_frame.winfo_rooty()


#        # 計算位置：貼齊 root 右側, 上側
        #x = root_x + frame_w - popup_width
        x = root_x + root_width + 10
        y = root_y - popup_height -50
#        # 設置 top 的位置（保持自動計算的大小）
        self.multiple_llm_selector_top.geometry(f"+{x}+{y}")
#        # 禁止調整大小（可選）
        self.multiple_llm_selector_top.resizable(False, False)

    def _on_multiple_llms_updated(self, new_list_llm_api_key):
        """當 LLMS API 更新時"""
        try:
            # 更新配置
            self.config_mgr.set_current_list_llm_api_key(new_list_llm_api_key)
            self.config_mgr.save_config()

            if len(new_list_llm_api_key) == 0:
                self.root.after(1, self.checkbox_multiple_llms.set_value(False))

            #self.show_info(self.translator.translate("success"),
            #               self.translator.translate("multiple_llms_settings_updated"))

        except Exception as e:
            print(f"更新 多重LLMS 配置時出錯: {e}")
            self.logger.error(f"更新 多重LLMS 配置時出錯: {e}")
            #self.show_error(self.translator.translate("error"),
            #                self.translator.translate("multiple_llms_settings_failed") + f": {str(e)}")

    def append_to_dialog_input(self, text: str, add_newline: bool = False, focus: bool = True):
        """
        將文字附加到輸入框

        Args:
            text: 要附加的文字
            add_newline: 是否在附加前添加換行符
            focus: 是否將焦點設置到輸入框
        """
        try:
            if not hasattr(self, 'dialog_input') or self.dialog_input is None:
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

    def _safe_append_to_input(self, text: str, add_newline: bool = False, focus: bool = True):
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
            if not hasattr(self, 'input_entry') or self.dialog_input is None:
                return False

            self.dialog_input.delete("1.0", tk.END)

            if keep_placeholder and hasattr(self, '_placeholder_text'):
                self.dialog_input.insert("1.0", self._placeholder_text)
                self.dialog_input.config(foreground='gray')

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
            if not hasattr(self, 'input_entry') or self.dialog_input is None:
                return ""

            text = self.dialog_input.get("1.0", tk.END)
            if strip:
                return text.strip()
            return text

        except Exception as e:
            self.logger.error(f"獲取輸入框文字時出錯: {e}")
            return ""

    def setup_memory(self):
        """設置伴侶對話框"""
        # 伴侶對話框框架
        print("setup_memory")
        memory_frame = ttk.LabelFrame(self.main_frame,
                                        # text=self.translator.translate("app_name"),
                                         width=400)
        memory_frame.grid(row=0, column=2, sticky="nswe", padx=(10, 0))
        memory_frame.grid_propagate(False)  # 重要：防止 grid 自動調整

        # 設定 grid 行的權重 (比例控制)
        # Row 0: Header (固定高度)
        # Row 1: Memory List (權重 50)
        # Row 2: Prompt (權重 10)
        # Row 3: Reply (剩餘空間)
        memory_frame.grid_rowconfigure(1, weight=50)
        memory_frame.grid_rowconfigure(2, weight=10)
        memory_frame.grid_rowconfigure(3, weight=30)  # 給予剩餘權重
        memory_frame.grid_columnconfigure(0, weight=1)

        # --- 1. 頭部 (Header) ---
        header_frame = ttk.Frame(memory_frame)
        header_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # 1.1 Title & 1.3 Settings Button
        title_row = ttk.Frame(header_frame)
        title_row.pack(fill=tk.X)

        ttk.Label(title_row, text=self.translator.translate("memory"),
                  font=(self.ui_font, self.ui_font_size - 1, "bold")).pack(side=tk.LEFT)

        self.settings_btn = ttk.Button(title_row, text=self.translator.translate('settings'),
                                       width=8, command=self._on_settings)
        self.settings_btn.pack(side=tk.RIGHT)

        # 1.2 Search Box
        self.search_memory = ttk.Entry(header_frame, font=(self.ui_font, self.ui_font_size - 1))
        self.search_memory.pack(fill=tk.X, pady=(5, 0))
        self.search_memory.insert(0, self.translator.translate("search_dialog") + "...")
        self.search_memory.bind('<FocusIn>', self._on_search_memory_focus_in)
        self.search_memory.bind('<FocusOut>', self._on_search_memory_focus_out)
        self.search_memory.bind('<KeyRelease>', self._on_memory_search_change)

        # 伴侶對話顯示區域
        memory_list_frame = ttk.Frame(memory_frame)
        memory_list_frame.grid(row=1, column=0, sticky="nswe", padx=5, pady=2)

        self.memory_list_display = scrolledtext.ScrolledText(
            memory_list_frame,
            wrap=tk.WORD,
            width=40,
            height=10,
            font=(self.ui_font, self.ui_font_size-1),
            background='#fafafa',
            foreground='black',
            relief=tk.FLAT
        )
        self.memory_list_display.pack(fill=tk.BOTH, expand=True)
        self.memory_list_display.config(state=tk.DISABLED)
        self.memory_list_display.tag_bind("memory-item-title", "<Enter>",
                                          lambda e: self.memory_list_display.config(cursor="hand2"))
        self.memory_list_display.tag_bind("memory-item-title", "<Leave>",
                                          lambda e: self.memory_list_display.config(cursor=""))

        # --- 3. 提取提示框 (Prompt) ---
        prompt_labelframe = ttk.LabelFrame(memory_frame, text= self.translator.translate("prompt"))
        prompt_labelframe.grid(row=2, column=0, sticky="nswe", padx=5, pady=2)


        #self.memory_prompt_display =  ReadOnlyScrolledText(
        self.memory_prompt_display = scrolledtext.ScrolledText(
            prompt_labelframe, wrap=tk.WORD, height=5,
            font=(self.mono_font, self.ui_font_size - 2),
            background='#f8f9fa'  # 淺灰色背景
        )
        self.memory_prompt_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2,)
        self.memory_prompt_display.config(state=tk.DISABLED)

        # --- 4. 儲存回覆框 (Reply) ---
        reply_labelframe = ttk.LabelFrame(memory_frame, text=self.translator.translate("reply"))
        reply_labelframe.grid(row=3, column=0, sticky="nswe", padx=5, pady=2)


       #self.memory_reply_display = scrolledtext.ScrolledText(
       #    reply_labelframe, wrap=tk.WORD, height=4,
       #    font=(self.ui_font, self.ui_font_size - 2),
       #    background='#f1f8e9'  # 淺綠色背景
       #)
        self.memory_reply_display = StreamingTextview(
            reply_labelframe,
            width=60,
            height=6
        )
        self.memory_reply_display.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        self.memory_reply_display.config(state=tk.DISABLED)

        self._load_memory_list()

    def _on_search_memory_focus_in(self, event):
        """搜索框獲得焦點"""
        if self.search_memory.get() == self.translator.translate("search_dialog") + "...":
            self.search_memory.delete(0, tk.END)
            self.search_memory.config(foreground='black')

    def _on_search_memory_focus_out(self, event):
        """搜索框失去焦點"""
        if not self.search_memory.get():
            self.search_memory.insert(0, self.translator.translate("search_dialog") + "...")
            self.search_memory.config(foreground='gray')

    def _on_memory_search_change(self, event):
        """當搜尋輸入改變時，過濾列表"""
        search_query = self.search_memory.get().strip()
        # 使用 after 延遲執行，避免輸入太快造成頻繁讀取檔案 (Debounce)
        if hasattr(self, '_search_after_id'):
            self.root.after_cancel(self._search_after_id)

        self._search_after_id = self.root.after(300, lambda: self._load_memory_list(search_query))

    def _load_memory_list(self, filter_query=None):
        """載入並顯示記憶列表"""
        try:
            # 從 memory_mgr 獲取清單 (如果有搜尋關鍵字則過濾)
            if filter_query:
                memories = self.memory_mgr.search_memories(filter_query)
            else:
                memories = self.memory_mgr.get_memory_id_title()

            self.memory_list_display.config(state=tk.NORMAL)
            self.memory_list_display.delete(1.0, tk.END)

            if not memories:
                self.memory_list_display.insert(tk.END, "尚無記憶記錄", "system-message")
            else:
                for item in memories:
                    # 建立一條可點擊的記錄顯示
                    display_text = f"📌 {item.get('title', '未命名')}\n"
                    time_str = item.get('updated_at', '').split('T')[0]  # 簡化日期顯示

                    start_index = self.memory_list_display.index(tk.INSERT)
                    self.memory_list_display.insert(tk.END, display_text, ("memory-item-title", item['id']))

            self.memory_list_display.config(state=tk.DISABLED)

            # 綁定點擊事件 (針對有 id tag 的文字)
            self.memory_list_display.tag_bind("memory-item-title", "<Button-1>", self._on_memory_item_click)

            # 設定樣式
            self.memory_list_display.tag_config("memory-item-title", foreground="#1a73e8", underline=True)
            self.memory_list_display.tag_config("memory-item-date", foreground="#888888",
                                                font=(self.ui_font, self.ui_font_size - 3))

        except Exception as e:
            self.logger.error(f"載入記憶列表失敗: {e}")

    def _on_memory_item_click(self, event):
        """點擊清單項目時，載入 Prompt 與 Reply 詳情"""
        try:
            # 獲取點擊位置的 tags
            index = self.memory_list_display.index(f"@{event.x},{event.y}")

            # 1. 處理高亮邏輯 (active tag)
            self.memory_list_display.config(state=tk.NORMAL)
            # 先移除所有現有的 active 高亮
            self.memory_list_display.tag_remove("active", "1.0", tk.END)

            # 獲取點擊那一行的起始與結束位置
            line_start = f"{index.split('.')[0]}.0"
            line_end = f"{index.split('.')[0]}.end"

            # 加入高亮
            self.memory_list_display.tag_add("active", line_start, line_end)
            self.memory_list_display.tag_config("active", background="#e8f0fe")
            self.memory_list_display.config(state=tk.DISABLED)

            tags = self.memory_list_display.tag_names(index)

            # 從 tags 中找到 UUID (假設 id tag 是唯一的)
            memory_id = None
            for tag in tags:
                if tag not in ["memory-item-title", "sel"]:  # 排除掉樣式用的 tag
                    memory_id = tag
                    break

            if memory_id:
                # 向 memory_mgr 請求詳細資料
                self.current_memory_dialog_id = memory_id
                detail = self.memory_mgr.get_memory_detail(memory_id)
                if detail:
                    self._update_memory_detail_views(
                        detail.get('prompt', ''),
                        detail.get('reply', '')
                    )
        except Exception as e:
            self.logger.error(f"讀取記憶詳情失敗: {e}")

    def _update_memory_detail_views(self, prompt, reply):
        """更新底下的 Prompt 與 Reply 顯示框"""
        # 更新 Prompt 框 (Extraction Process)
        self.memory_prompt_display.config(state=tk.NORMAL)
        self.memory_prompt_display.delete(1.0, tk.END)
        self.memory_prompt_display.insert(tk.END, prompt)
        self.memory_prompt_display.config(state=tk.DISABLED)

        # 更新 Reply 框 (Stored Content)
        self.memory_reply_display.clear()
        self.memory_reply_display.display_text(reply, is_streaming=False, is_markdown=True, is_typewriter=False)
        #self.memory_reply_display.config(state=tk.NORMAL)
        #self.memory_reply_display.delete(1.0, tk.END)
        #self.memory_reply_display.config(state=tk.DISABLED)

    def _on_settings(self):
        """開啟路徑設定"""
        try:
            self.settings_top_level = tk.Toplevel(self.root)
            self.settings_top_level.title(self.translator.translate("settings"))
            self.settings_top_level.transient(self.root)
            self.settings_top_level.grab_set()

            self.settings_frame = ttk.Frame(self.settings_top_level, padding=10)
            self.settings_frame.pack(side=tk.RIGHT)

            # LLM 設定按鈕
            row = 0
            self.mind_btn = ttk.Button(self.settings_frame, text=self.translator.translate('mind_settings'),
                                       width=15, command=self._on_mind_settings)
            self.mind_btn.grid(row=row, column=0, pady=5)

            row += 1
            self.llm_settings_btn = ttk.Button(
                self.settings_frame,
                text=self.translator.translate('llm_settings'),
                width=15,
                command=self._on_llm_settings
            )
            self.llm_settings_btn.grid(row=row, column=0, pady=5)

            #self.memory_settings_btn = ttk.Button(
            #    self.settings_frame,
            #    text=self.translator.translate('memory_settings'),
            #    # keep it simple; replace with translator key if you have one
            #    width=15,
            #    command=self._on_memory_settings
            #)
            #self.memory_settings_btn.grid(row=1, column=0, pady=5)
            row+=1
            self.profile_btn = ttk.Button(self.settings_frame, text=self.translator.translate('edit_basic_profile'),width=15, command=self.show_profile_settings_window)
            self.profile_btn.grid(row=row, column=0, pady=5)


            # 重要：先更新窗口讓系統計算實際大小
            self.settings_top_level.update_idletasks()

            # 獲取 top 的實際大小
            popup_width = self.settings_top_level.winfo_width()
            popup_height = self.settings_top_level.winfo_height()

            # 獲取 root 的位置
            root_x = self.root.winfo_x()
            root_y = self.root.winfo_y()
            root_width = self.root.winfo_width()

            # 計算位置：貼齊 root 右側
            x = root_x + root_width - popup_width -50
            y = root_y + 100

            # 設置 top 的位置（保持自動計算的大小）
            self.settings_top_level.geometry(f"+{x}+{y}")

            # 禁止調整大小（可選）
            self.settings_top_level.resizable(False, False)

        except Exception as e:
            self.logger.error(f"_on_settings 出錯: {e}")
            self.show_error(self.translator.translate("error"),
                            f"Cannot open Paths settings: {str(e)}")  # 載入當前路徑配置

    def _on_llm_settings(self):
        """開啟 LLM 設定"""
        try:
            # 導入 LLMS 編輯器


            # 載入當前 LLMS 配置
            llms_api = self.config_mgr.get_llms_api()

            # 創建編輯器
            editor = Editor_LLMS_API(
                parent=self.settings_frame,
                callback=self._on_llms_updated,
                translator=self.translator,
                llms_api=llms_api
            )
            editor.lift()

            width = editor.get_width()
            root_x = self.settings_top_level.winfo_x()
            root_y = self.settings_top_level.winfo_y()
            root_width = self.settings_top_level.winfo_width()

            # 計算位置：貼齊 root 右側
            x = root_x - width - 10
            y = root_y

            # 設置 top 的位置（保持自動計算的大小）
            editor.geometry(f"+{x}+{y}")


        except ImportError as e:
            self.logger.error(f"無法載入 LLMS 編輯器: {e}")
            self.show_warning(self.translator.translate("function_not_available"), self.translator.translate("llm_editor_not_available"))
        except Exception as e:
            self.logger.error(f"開啟 LLM 設定時出錯: {e}")
            self.show_error(self.translator.translate("error"), self.translator.translate("cannot_open_LLM_settings")+f": {str(e)}")


    def _on_mind_settings(self):
        """開啟路徑設定"""
        try:
            top = tk.Toplevel(self.settings_frame)
            top.title(self.translator.translate("mind_settings"))
            top.transient(self.settings_frame)
            top.grab_set()

            frm = ttk.Frame(top, padding=10)
            frm.pack(fill=tk.BOTH, expand=True)
            row = 0
            Filepath_Selector(parent=frm,
                              label=self.translator.translate("data_dir"),
                              label_for_button_pick=self.translator.translate("select"),
                              is_dir=True,
                              var=self.config_mgr.get_data_dir(),
                              callback=self._on_data_dir_updated,
                              ).grid(row=0, column=0)
            row += 1
            Text_Editor(parent=frm, label=self.translator.translate("max_reference_history_dialogs"),
                        var=self.config_mgr.get_max_reference_history_dialogs(),
                        callback=self._on_max_ref_dialogs_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")
            row+=1
            Text_Editor(parent=frm, label=self.translator.translate("max_history_ai_suggestions"),
                        var=self.config_mgr.get_max_history_ai_suggestions(),
                        callback=self._on_max_history_ai_suggestions_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")
            row += 1
            Text_Editor(parent=frm, label=self.translator.translate("mind_check_interval"),
                        var=self.config_mgr.get_mind_check_interval(),
                        callback=self._on_mind_check_interval_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")
            row += 1
            Text_Editor(parent=frm, label=self.translator.translate("mind_check_interval_initial"),
                        var=self.config_mgr.get_mind_check_interval_initial(),
                        callback=self._on_mind_check_interval_initial_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")

            row += 1
            Text_Editor(parent=frm, label=self.translator.translate("todo_check_interval"),
                        var=self.config_mgr.get_todo_check_interval(),
                        callback=self._on_todo_check_interval_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")
            row += 1
            Text_Editor(parent=frm, label=self.translator.translate("mind_idle_waiting_time"),
                        var=self.config_mgr.get_mind_idle_waiting_time(),
                        callback=self._on_mind_idle_waiting_time_updated,
                        ).grid(row=row, column=0, field_width=10, sticky="w")
            row += 1
            label_user_focus = ttk.Label(frm, text=self.translator.translate("user_focus"))
            label_user_focus.grid(row=row, column=0, sticky="w")
            row += 1
            Scroll_Text_Editor(parent=frm,
                        var=self.config_mgr.get_user_focus(),
                        callback=self._on_user_focus_updated,
                        ).grid(row=row, column=0, scroll_width=40, scroll_height=20,  sticky="w")

            top.update_idletasks()

            # 獲取 top 的實際大小
            popup_width = top.winfo_width()
            popup_height = top.winfo_height()

            # 獲取 root 的位置
            root_x = self.settings_top_level.winfo_x()
            root_y = self.settings_top_level.winfo_y()
            root_width = self.settings_top_level.winfo_width()

            # 計算位置：貼齊 root 右側
            x = root_x - popup_width - 10
            y = root_y

            # 設置 top 的位置（保持自動計算的大小）
            top.geometry(f"+{x}+{y}")

            # 禁止調整大小（可選）
            top.resizable(False, False)
        except Exception as e:
            self.logger.error(f"_on_mind_settings 出錯: {e}")
            self.show_error(self.translator.translate("error"), f"Cannot open Paths settings: {str(e)}")  # 載入當前路徑配置

    def _on_llms_updated(self, new_llms_api: LLMS_API):
        """當 LLMS API 更新時"""
        try:
            # 更新配置
            self.config_mgr.set_llms_api(new_llms_api)
            list_key = new_llms_api.get_list_key()
            self.llm_selector.config(combo_source=list_key)
            self.llm_selector.build_ui()
            if self.list_checkbox_llms:
                self.list_checkbox_llms.config(list_source = list_key)
                self.list_checkbox_llms.build_ui()

          #  self.show_info(self.translator.translate("success"), self.translator.translate("llm_settings_updated"))

        except Exception as e:
            self.logger.error(f"更新 LLMS 配置時出錯: {e}")
            self.show_error(self.translator.translate("error"), self.translator.translate("llm_settings_failed")+f": {str(e)}")
    
    def _on_data_dir_updated(self, new_dir):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_dir:
                return
            self.config_mgr.set_data_dir(new_dir)
            self.config_mgr.save_config()
        except Exception as e:
            self.logger.error(f"_on_data_dir_updated出錯: {e}")

    def _on_max_ref_dialogs_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_max_reference_history_dialogs( int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_max_ref_dialogs_updated出錯: {e}")

    def _on_mind_check_interval_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_mind_check_interval( int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_mind_check_interval_updated出錯: {e}")

    def _on_mind_check_interval_initial_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_mind_check_interval_initial( int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_mind_check_interval_initial_updated出錯: {e}")
    def _on_todo_check_interval_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_todo_check_interval(int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_mind_check_interval_updated出錯: {e}")

    def _on_mind_idle_waiting_time_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_mind_idle_waiting_time(int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_mind_check_interval_updated出錯: {e}")

    def _on_max_history_ai_suggestions_updated(self, new_number_str):
        """當記憶路徑更新時"""
        try:
            # 更新配置
            if not new_number_str:
                return
            self.config_mgr.set_max_history_ai_suggestions(int(new_number_str))
        except Exception as e:
            self.logger.error(f"_on_mind_check_interval_updated出錯: {e}")

    def _on_user_focus_updated(self, new_focus):
        """當記憶路徑更新時"""
        try:
            self.config_mgr.set_user_focus(new_focus)
        except Exception as e:
            self.logger.error(f"_on_user_focus_updated 出錯: {e}")

    def show_profile_settings_window(self):
        """彈出用戶基本資料設定視窗"""
        profile_top = tk.Toplevel(self.settings_frame)
        profile_top.title("個人化設定 (Basic Profile)")
        profile_top.geometry("400x500")

        # --- 關鍵：處理右上角關閉按鈕 ---
        def on_close():
            # 你可以在這裡加入「尚未儲存，確定關閉？」的提醒
            profile_top.destroy()

        profile_top.protocol("WM_DELETE_WINDOW", on_close)

        profile_frame = ttk.Frame(profile_top)
        profile_frame.pack(fill=tk.BOTH, expand=True)

        # 讀取現有資料
        user_profile = self.memory_mgr.get_user_profile() or { "basic":{}, "extracted":{} }
        user_profile_basic = user_profile.get("basic", {})

        # UI 佈局
        fields = [
            ("name", self.translator.translate("your_name")),
            ("occupation", self.translator.translate("occupation")),
            ("language_preferred", self.translator.translate("language_preferred")),
            ("ai_reply_style_preferred", self.translator.translate("ai_reply_style_preferred")),
            ("forbidden_topics", self.translator.translate("forbidden_topics"))
        ]

        entries = {}
        for i, (key, label) in enumerate(fields):
            ttk.Label(profile_frame, text=label).pack(pady=(10, 0), padx=20, anchor="w")
            entry = ttk.Entry(profile_frame, width=40)
            entry_value = str(user_profile_basic.get(key, ""))
            if key == "forbidden_topics":
                list_forbidden_topic = user_profile_basic.get(key, [])
                entry_value = ",".join(list_forbidden_topic)
            entry.insert(0, entry_value )
            entry.pack(pady=5, padx=20)
            entries[key] = entry

        def save_and_close():
            # 整理數據
            new_basic = {key: entry.get() for key, entry in entries.items()}
            # 特殊處理逗號分隔
            new_basic["forbidden_topics"] = [x.strip() for x in new_basic["forbidden_topics"].split(",") if x.strip()]

            user_profile["basic"] = new_basic

            # 儲存
            self.memory_mgr.save_user_profile(user_profile)
            self.logger.info("用戶手動設定已更新")
            profile_top.destroy()

        style = ttk.Style()
        style.configure("Green.TButton",
                        background="#4CAF50",
                        foreground="white")
        button = ttk.Button(profile_frame, text=self.translator.translate("save"), command=save_and_close, style="Green.TButton")
        button.pack(pady=20)

        profile_top.update_idletasks()

        # 獲取 top 的實際大小
        popup_width = profile_top.winfo_width()
        popup_height = profile_top.winfo_height()

        # 獲取 root 的位置
        root_x = self.settings_top_level.winfo_x()
        root_y = self.settings_top_level.winfo_y()
        root_width = self.settings_top_level.winfo_width()

        # 計算位置：貼齊 root 右側
        x = root_x - popup_width - 10
        y = root_y

        # 設置 top 的位置（保持自動計算的大小）
        profile_top.geometry(f"+{x}+{y}")

        # 禁止調整大小（可選）
        profile_top.resizable(False, False)

    def set_callbacks(self, message_callback, voice_callback, file_callback):
        """設置回調函數"""
        self.user_prompt_callback = message_callback
        self.voice_callback = voice_callback
        self.file_callback = file_callback



    def cleanup(self):
        """清理資源"""
        if hasattr(self, 'dialogs_display'):
            self.dialogs_display.cleanup()

    def reset(self):
        if hasattr(self, 'dialogs_display'):
            self.dialogs_display.reset()

    # 事件處理
    def _on_send_user_prompt(self):
        """發送消息"""
        user_prompt = self.dialog_input.get("1.0", tk.END).strip()
        if user_prompt and self.user_prompt_callback:
            self.dialog_input.delete("1.0", tk.END)
            self.user_prompt_callback(user_prompt)
    
    def _on_voice_input(self):
        """語音輸入"""
        if self.voice_callback:
            self.voice_callback()
    
    def _on_file_upload(self):
        """文件上傳"""
        if self.file_callback:
            file_types = [
                (self.translator.translate("all_supported_files"), "*.txt *.md *.pdf *.jpg *.png *.doc *.docx"),
                (self.translator.translate("text_files"), "*.txt"),
                (self.translator.translate("md_files"), "*.md"),
                (self.translator.translate("pdf_files"), "*.pdf"),
                (self.translator.translate("image_files"), "*.jpg *.png"),
                (self.translator.translate("word_files"), "*.doc *.docx")
            ]
            
            file_paths = filedialog.askopenfilenames(
                title=self.translator.translate("select_files"),
                filetypes=file_types
            )
            
            if file_paths:
                self.file_callback(list(file_paths))
    

    
    def _on_dialog_input_enter_pressed(self, event):
        """回車鍵處理"""
        if not event.state & 0x1:  # 沒有按住 Shift
            self._on_send_user_prompt()
            return "break"  # 阻止默認行為
        return None
    
    def _on_dialog_input_shift_enter_pressed(self, event):
        """Shift+Enter 處理 - 換行"""
        return None  # 允許默認行為（換行）
    
    def _on_search_history_focus_in(self, event):
        """搜索框獲得焦點"""
        if self.search_history.get() == self.translator.translate("search_dialog")+ "...":
            self.search_history.delete(0, tk.END)
            self.search_history.config(foreground='black')
    
    def _on_search_history_focus_out(self, event):
        """搜索框失去焦點"""
        if not self.search_history.get():
            self.search_history.insert(0, self.translator.translate("search_dialog") + "...")
            self.search_history.config(foreground='gray')

    def _on_search_history_key_release(self, event):
        """搜索鍵釋放"""
        search_text = self.search_history.get().strip()

        if search_text == self.translator.translate("search_dialog")+"..." or not search_text:
            # 顯示所有對話
            self.update_history_list()
            return

        try:
            # 清空列表
            self.history_listbox.delete(0, tk.END)

            # 搜索對話
            results = self.history_mgr.search_in_dialogs(search_text)

            for dialog in results:
                title = f"{dialog.title}\n{dialog.updated_at[:16]}"
                self.history_listbox.insert(tk.END, title)

            self.logger.info(f"搜索 '{search_text}' 找到 {len(results)} 個結果")

        except Exception as e:
            self.logger.error(f"搜索對話時出錯: {e}")

    def _on_historical_dialog_select(self, event):
        """選擇對話歷史"""
        selection = self.history_listbox.curselection()
        if selection:
            index = selection[0]
            dialogs = self.history_mgr.get_all_dialogs()

            if index < len(dialogs):
                dialog = dialogs[index]
                self.current_history_dialog_id = dialog.id
                self.root.after(0,self.display_dialog, dialog)



    def add_new_dialog_message(self, user_prompt: str, llm_response: str, title: str):
        """添加新的對話記錄到 History"""
        try:
            # 創建新對話記錄
            if  self.current_history_dialog_id:
                if title:
                    self.history_mgr.change_title(self.current_history_dialog_id, title)
                self.history_mgr.add_message_to_dialogs_history(self.current_history_dialog_id, "user", user_prompt)
                self.history_mgr.add_message_to_dialogs_history(self.current_history_dialog_id, "ai", llm_response)
            else:
                self.current_history_dialog_id = self.history_mgr.create_dialog(
                user_prompt, llm_response, title
            )

            if self.current_history_dialog_id:

                # 更新側邊欄列表
                self.update_history_list()

                # 選中新對話
                self.history_listbox.selection_clear(0, tk.END)
                self.history_listbox.selection_set(0)
                self.history_listbox.see(0)

                self.logger.info(f"已創建新對話記錄: {self.current_history_dialog_id}")

        except Exception as e:
            self.logger.error(f"添加新對話記錄時出錯: {e}")


   #def _new_dialog(self):
   #    """新建對話"""
   #   # self.current_conversation = []
   #    self.dialogs_display.config(state=tk.NORMAL)
   #    self.dialogs_display.delete(1.0, tk.END)
   #    self.dialogs_display.config(state=tk.DISABLED)

   #    self.display_dialog_message(
   #        {"role": "system", "content": "開始新對話", "timestamp": datetime.now()}
   #    )

    
    def show_error(self, title: str, message: str):
        """顯示錯誤對話框"""
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """顯示信息對話框"""
        messagebox.showinfo(title, message)
    
    def show_warning(self, title: str, message: str):
        """顯示警告對話框"""
        messagebox.showwarning(title, message)