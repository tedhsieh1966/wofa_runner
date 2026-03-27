"""
WofaRunner 主應用程式
協調所有模組的運作 - 修正版
"""

import json
import re
import tkinter as tk
from tkinter import messagebox
import logging
from datetime import datetime
from operator import truediv
from pathlib import Path

# 修正導入路徑
import os
import sys
import platform
import threading
import asyncio
import queue
import copy
from typing import Optional, Dict, List, Any

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


from wofa_server.wofa_service import *
from py_libraries.LanguageOp import LanguageTranslator, get_current_input_language
from py_libraries.SpeechRecognizer import StreamingSpeechRecognizer
from src.ui import WofaRunnerUI
from src.wfa_manager import WfaManager

IS_LOG = False

# === 常數配置 ===
TEMP_DIR_BASE = "c:/temp"
ICON_PATH = "favicon.ico"
DEFAULT_WFA = "default.wfa"
EOS_PATTERN = "END_OF_STREAMING"
DEFAULT_WORK_STAGE = "agent_run"

# 配置日誌 - 根據 IS_LOG 設置級別
if IS_LOG:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
else:
    # 禁用日誌輸出
    logging.basicConfig(level=logging.CRITICAL)

# 资源路径处理函数


def get_base_dir():
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)  # 打包后：exe所在文件夹
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # 开发时：脚本所在文件夹
    return base_dir


def get_full_dir(relative_dir) -> Optional[str]:
    """获取资源的绝对路径"""
    try:
        base_dir = get_base_dir()
        full_dir = os.path.join(base_dir, relative_dir)
        if not os.path.exists(full_dir):
            os.makedirs(full_dir)

        return str(full_dir)
    except Exception as e:
        return None


def get_full_path(relative_path):
    """获取资源的绝对路径"""
    try:
        # if hasattr(sys, '_MEIPASS'):
        base_dir = get_base_dir()

        full_path = os.path.join(base_dir, relative_path)

        if not os.path.exists(full_path):
            logging.error(f"资源文件未找到: {full_path}")
            messagebox.showerror("錯誤", f"找不到必需的文件: {relative_path}")
            return None

        return full_path
    except Exception as e:
        logging.error(f"资源路径错误: {str(e)}")
        messagebox.showerror("錯誤", f"無法定位資源文件: {str(e)}")
        return None


# 加载资源文件
excel_path = get_full_path("languages.xlsx")
if excel_path:
    logging.info(f"资源文件找到: {excel_path}")
else:
    messagebox.showerror("錯誤", "無法加載語言文件，應用程序將關閉")
    sys.exit(1)


class AsyncEventLoop:
    """管理异步事件循环"""

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger("AsyncEventLoop")
        self.loop = None
        self.thread = None
        self.running = False

    def start(self):
        """启动异步事件循环线程"""
        if self.running:
            return

        def run_loop():
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                self.running = True
                self.logger.info("异步事件循环已启动")
                self.loop.run_forever()
            except Exception as e:
                self.logger.error(f"事件循环运行出错: {e}")
            finally:
                self.running = False

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止事件循环"""
        if self.loop and self.running:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.running = False
            self.logger.info("异步事件循环已停止")

    def run_coroutine(self, coroutine):
        """安全运行协程"""
        if not self.loop or not self.running:
            self.logger.error("事件循环未运行")
            return None

        try:
            future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
            return future
        except Exception as e:
            self.logger.error(f"运行协程失败: {e}")
            return None


class WofaRunnerApp:
    def __init__(self):
        self.logger = logging.getLogger("WofaRunner.App")

        self.translator = LanguageTranslator(get_full_path("languages.xlsx"))
        available_languages = self.translator.get_languages()
        sys_lang = get_current_input_language()
        if len(sys.argv) > 2 and sys.argv[2] in available_languages:
            self.my_language = sys.argv[2]
        else:
            sys_lang_name = sys_lang.get("language_name")
            if sys_lang_name in available_languages:
                self.my_language = sys_lang_name
            else:
                self.my_language = available_languages[0]
        self.translator.set_current_language(self.my_language)

        """初始化 應用程式"""
        self.root = tk.Tk()
        self.setup_root_window()
        if platform.system() != "Darwin":
            self.voice_recognition = StreamingSpeechRecognizer(
                language=sys_lang.get("iso_code")
            )
        self.async_loop = AsyncEventLoop(self.logger)
        self.async_loop.start()

        self.wofa_service = WofaService(
            temp_dir_base=TEMP_DIR_BASE,
            callback=self.on_wofa_response,
        )

        # 執行緒安全鎖
        self._lock = threading.Lock()

        self.current_user_prompt = None
        self.categorize_result = None
        self.current_llm_response = None
        self.list_file_to_upload = []
        self.last_ai_question = ""
        self.last_ai_suggestion = {}
        self.todo_list = []
        self.work_stage = DEFAULT_WORK_STAGE

        # 消息隊列
        self.message_queue = queue.Queue()
        self.running = True
        self.eos_pattern = EOS_PATTERN
        self.eos_buffer = ""
        self.is_eos = False
        self.is_matching = False
        self.is_waiting_user_answer = False
        self.is_user_requesting = False
        #
        # 初始化 UI - 修正參數傳遞
        self.ui = WofaRunnerUI(self.root, translator=self.translator)
        self.ui.set_callbacks(
            voice_callback=self.on_voice_input,
            pending_user_input_callback=self.on_pending_user_input
        )
        # 載入 WFA（從 argv[1]）並顯示名稱
        self.wfa_mgr = WfaManager()
        wfa_name = self.wfa_mgr.wfa_path_str
        if wfa_name:
            self.ui.set_wfa_name(wfa_name)

        # 啟動處理線程
        self.start_processing_thread()
        self.launch_agent()

        self.logger.info("WofaRunner 應用程式初始化完成")

    def setup_root_window(self):
        """設置主視窗"""
        self.root.title(self.translator.translate("app_name"))
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # if sys.platform == 'win32':
        #    # Windows: 使用 zoomed
        #    self.root.state('zoomed')
        # elif sys.platform == 'darwin':  # macOS
        #    # macOS: 获取屏幕尺寸并设置窗口大小
        #    screen_width = self.root.winfo_screenwidth()
        #    screen_height = self.root.winfo_screenheight()
        #    self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        #    # 可选：隐藏菜单栏获得更多空间
        #    self.root.attributes('-fullscreen', False)  # 设置为False以避免真全屏
        # else:  # Linux 或其他系统
        #    self.root.attributes('-zoomed', True)

        # 設置圖標
        try:
            icon_path = get_full_path(ICON_PATH)
            if icon_path and Path(icon_path).exists():
                self.root.iconbitmap(str(icon_path))
        except Exception:
            pass

    def on_user_input(self, text: str):
        """用戶發送文本消息"""
        self.message_queue.put(
            {"type": "user_input", "user_input_text": text, "timestamp": datetime.now()}
        )

    def on_wait_user_input(self, text: str):
        """用戶發送文本消息"""
        self.message_queue.put(
            {"type": "wait_user_input", "prompt": text, "timestamp": datetime.now()}
        )

    def on_voice_input(self):
        """用戶啟動語音輸入"""
        self.message_queue.put({"type": "voice_input", "timestamp": datetime.now()})

    def launch_agent(self):
        """處理用戶文本消息 - 開始三輪 LLM 互動"""
        try:
            # 使用 lambda 或直接呼叫產生 coroutine
            future = self.async_loop.run_coroutine(self._start_agent_run())

            if not future:
                self._handle_error_response(
                    self.translator.translate("cannot_launch_agent")
                )
        except Exception as e:
            error_msg = f"launch_agent 時出錯: {str(e)}"
            self.logger.error(error_msg)

    def on_pending_user_input(self, user_input:str):
        self.wofa_service.project.append_pending_user_input(user_input)

    def handle_user_input(self, message: dict[str, Any]):
        """處理用戶文本消息 - 開始三輪 LLM 互動"""
        try:
            prompt = message["prompt"]
            timestamp = message["timestamp"]

            # 保存當前用戶提示
            self.current_user_prompt = prompt

            # 在主線程中顯示用戶消息
            if prompt:
                self.root.after(0, self.ui.display_ai_message, prompt, False, timestamp)

            self.logger.info("開始分類提示詞...")

            # 定義映射表，Key 是 stage，Value 是對應的 method (不加括號)
            stage_map = {
                "agent_run": self._start_agent_run,
            }

            # 取得對應的 method，若找不到則回傳預設的 _start_user_request
            target_func = stage_map.get(self.work_stage, self._start_agent_run)

            # 使用 lambda 或直接呼叫產生 coroutine
            future = self.async_loop.run_coroutine(target_func(prompt))

            if not future:
                self._handle_error_response(
                    self.translator.translate("cannot_start_workflow")
                )

        except Exception as e:
            error_msg = f"處理用戶消息時出錯: {str(e)}"
            self.logger.error(error_msg)
            timestamp = datetime.now()
            self.root.after(0, self.ui.display_ai_message, error_msg, timestamp)
            self.root.after(0, self.ui.complete_ai_streaming)

    def handle_std_output(self, message: dict[str, Any]):
        """處理用戶文本消息 - 開始三輪 LLM 互動"""
        try:
            user_prompt = message["user_prompt"]
            timestamp = message["timestamp"]

            # 保存當前用戶提示
            self.current_user_prompt = user_prompt

            # 在主線程中顯示用戶消息
            self.root.after(0, self.ui.display_user_message, user_prompt, timestamp)

            self.logger.info("開始分類提示詞...")

            # 定義映射表，Key 是 stage，Value 是對應的 method (不加括號)
            stage_map = {
                "agent_run": self._start_agent_run,
            }

            # 取得對應的 method，若找不到則回傳預設的 _start_user_request
            target_func = stage_map.get(self.work_stage, self._start_agent_run)

            # 使用 lambda 或直接呼叫產生 coroutine
            future = self.async_loop.run_coroutine(target_func(user_prompt))

            if not future:
                self._handle_error_response(
                    self.translator.translate("cannot_start_workflow")
                )

        except Exception as e:
            error_msg = f"處理用戶消息時出錯: {str(e)}"
            self.logger.error(error_msg)
            timestamp = datetime.now()
            self.root.after(0, self.ui.display_ai_message, error_msg, timestamp)
            self.root.after(0, self.ui.complete_ai_streaming)

    async def _start_agent_run(self, user_prompt: Optional[str] = None):
        try:
            self.is_eos = False
            self.is_matching = False
            self.eos_buffer = ""
            project_file_content = self.wfa_mgr.get_wfa_str()
            self.ui.start_ai_streaming()
            result = await self.wofa_service.start_workflow_async(
                project_file_content=project_file_content,
                user_prompt=user_prompt,
            )
            self.logger.info(f"詢問工作流程已啟動，任務ID: {result.get('task_id')}")

        except Exception as e:
            self.logger.error(f"啟動詢問工作流程時出錯: {e}")
            self._handle_error_response(
                f"{self.translator.translate('ask_failed')}: {str(e)}"
            )

    def on_wofa_response(
        self,
        tag: str,
        task_id: str,
        status: str,
        response: dict[str, Any],
        node: Optional[Any] = None,
    ):
        """處理 WofaService 的回應"""
        try:
            if tag == LABEL_LLM_REPLY:
                message = response.get("llm_reply", "")
                message_streaming = response.get("llm_reply_streaming", "")

                if status in ["completed", "streaming"]:
                    if message_streaming:
                        self._handle_agent_run_response(message_streaming, status)
                    if message:
                        self._handle_agent_run_response(message, status)

                elif status == "error":
                    self._handle_error_response(message)

                # 完成任務
                if status in ["completed", "error"]:
                    self.wofa_service.finish_task(task_id)
            if tag == LABEL_STD_OUTPUT:
                std_output = response["std_output"]
                style = None
                is_markdown = False
                is_typewriter = False
                style_name = "std_output"
                text = "No text for std output"
                if isinstance(std_output, dict):
                    text = std_output.get("text")
                    display_effect_str = std_output.get("display_effect_str")
                    display_effect: dict = json.loads(display_effect_str)
                    style = display_effect.get("style", None)
                    style_name = display_effect.get("style_name", "std_output")
                    is_markdown = display_effect.get("is_markdown", False)
                    is_typewriter = display_effect.get("is_typewriter", False)
                elif isinstance(std_output, str):
                    text = std_output
                if style:
                    style_name = "custom_style"
                    self.ui.add_custom_style(style_name=style_name, style=style)
                self.root.after(
                    0,
                    self.ui.display_std_output,
                    text,
                    style_name,
                    is_markdown,
                    is_typewriter,
                )
            if tag == LABEL_WAIT_USER_INPUT:
                self.ui.on_waiting_user_input(response["prompt"], node)

        except Exception as e:
            self.logger.error(
                f"處理 WofaService 回應時出錯: {e} in response {response}"
            )
            # self._handle_error_response(str(e))

    def _handle_agent_run_response(self, _message: str, status: str):
        with self._lock:
            message = copy.copy(_message)
            self.logger.info(
                f"_handle_agent_run_response status={status} message={message}"
            )
            """處理詢問問題回應"""
            if status == "completed":
                self.handle_completed_message(message)
            elif status == "streaming":
                self.handle_streaming_message(message)

    def handle_completed_message(self, message, is_save=True):
        with self._lock:
            if self.eos_pattern in message:
                parts = message.split(self.eos_pattern)
                self.current_llm_response = parts[0].strip()
                self.logger.info("LLM 回應完成")
                # 確保所有 streaming 內容都已顯示
                self.root.after(0, self.ui.complete_ai_streaming)

                # 結構化數據（隱藏的 JSON）
                content_json_str = parts[1].strip() if len(parts) > 1 else ""
            else:
                content_json_str = message

            structured_reply = None
            if content_json_str:
                try:
                    structured_reply = json.loads(content_json_str)
                    self.logger.info("解析到結構化記憶數據")
                except Exception as e:
                    self.logger.error(f"解析 JSON 失敗: {e}")

        self.ui.reset()

    def handle_streaming_message(self, message):
        with self._lock:
            if message and not self.is_eos:
                i = 0
                # 遍歷當前 chunk 進行 EOS 匹配
                while i < len(message):
                    char = message[i]
                    # 取得預期匹配的下一個 EOS 字符
                    expected_eos_char = self.eos_pattern[len(self.eos_buffer)]

                    if char == expected_eos_char:
                        if i > 0 and not self.is_matching:
                            chunk_trimmed = message[:i]
                            self.root.after(
                                0, self.ui.display_ai_message, message[:i], True
                            )
                            message = message[i:]
                            i = 0

                        self.is_matching = True
                        self.eos_buffer += char

                        # 如果完整匹配成功
                        if self.eos_buffer == self.eos_pattern:
                            self.is_eos = True
                            break
                    else:
                        if len(self.eos_buffer) > 0:
                            self.eos_buffer = ""
                            self.is_matching = False

                    i += 1

                if not self.is_matching and not self.is_eos:
                    # 只有尚未偵測到 EOS 的內容才發送到 UI
                    self.root.after(0, self.ui.display_ai_message, message, True)

    def _handle_error_response(self, error_message: str):
        """處理錯誤回應"""
        self.logger.error(f"Wofa Serivce 回應的錯誤: {error_message}")
        timestamp = datetime.now()
        self.root.after(0, self.ui.display_ai_message, f"錯誤: {error_message}", False)
        self.root.after(0, self.ui.complete_ai_streaming)

        # 重置對話狀態
        self._reset_dialog_state()

    def start_processing_thread(self):
        """啟動消息處理線程"""
        self.process_thread = threading.Thread(target=self._process_messages)
        self.process_thread.daemon = True
        self.process_thread.start()
        self.logger.info("消息處理線程已啟動")

    def _process_messages(self):
        """處理消息隊列（不使用非同步）"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                self.handle_message(message)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"處理消息時出錯: {e}")

    def handle_message(self, message: dict[str, Any]):
        """處理消息"""
        msg_type = message.get("type")

        if msg_type == "user_input":
            self.handle_user_input(message)
        elif msg_type == "std_output":
            self.handle_std_output(message)
        elif msg_type == "voice_input":
            self.handle_voice_input(message)

    def _reset_dialog_state(self):
        """重置對話狀態"""
        self.work_stage = "user_request"
        self.current_user_prompt = None
        self.categorize_result = None
        self.current_llm_response = None

    def handle_voice_input(self, message: dict[str, Any]):
        """處理語音輸入 - 流式識別版本"""
        try:
            timestamp = message["timestamp"]

            # 檢查是否已在流式識別中
            if hasattr(self, "_is_voice_streaming") and self._is_voice_streaming:
                # 如果已在識別中，停止它
                self._is_voice_streaming = False
                self.ui.voice_btn.config(
                    text="🎤 " + self.translator.translate("voice_input")
                )

                # 停止語音識別
                if hasattr(self.voice_recognition, "stop_streaming_recognition"):
                    self.voice_recognition.stop_streaming_recognition()

                return

            # 設置流式識別狀態
            self._is_voice_streaming = True
            self.ui.voice_btn.config(
                text="⏹️ " + self.translator.translate("stop_voice_input")
            )
            self._voice_stream_text = ""  # 累積的識別文字
            self._voice_streaming_dots = 0  # 動態點數計數器

            # 聚焦到輸入框
            self.root.after(0, self.ui.dialog_input.focus_set)

            # 開始流式語音識別
            if hasattr(self.voice_recognition, "start_streaming_recognition"):
                self.voice_recognition.start_streaming_recognition(
                    callback=lambda text, complete: self._on_voice_stream_update(
                        text, complete, timestamp
                    )
                )
            else:
                # 如果沒有流式功能，使用舊的識別方法
                self._use_legacy_voice_recognition(timestamp)

        except Exception as e:
            error_msg = f"{self.translator.translate('start_voice_recognition_failed')}: {str(e)}"
            self.logger.error(error_msg)
            timestamp = message["timestamp"]
            self._is_voice_streaming = False

    def _on_voice_stream_update(self, text_chunk: str, is_complete: bool, timestamp):
        """處理流式語音識別更新"""

        def update_ui():
            if is_complete:
                # 流式識別完成
                self._is_voice_streaming = False

                if hasattr(self, "_voice_stream_text") and self._voice_stream_text:
                    # 最終確認

                    # 確保輸入框有完整文字並聚焦
                    final_text = self._voice_stream_text.strip()
                    # if final_text:
                    # 將識別結果附加到輸入框（不清空原有內容）
                    # self.ui.append_to_dialog_input(final_text, True, True)

            else:
                # 流式更新
                if text_chunk and text_chunk.strip():
                    # 累積文字
                    self._voice_stream_text = text_chunk

                    # 更新輸入框
                    current_text = self.ui.dialog_input.get("1.0", tk.END).strip()

                    # 智能合併文字
                    if current_text:
                        # 檢查是否有重疊部分
                        overlap = self._find_text_overlap(current_text, text_chunk)
                        if overlap:
                            new_part = text_chunk[len(overlap) :]
                            if new_part.strip():
                                new_text = current_text + new_part
                                self.ui.dialog_input.delete("1.0", tk.END)
                                self.ui.dialog_input.insert("1.0", new_text)
                        else:
                            new_text = (
                                current_text + " " + text_chunk
                                if current_text
                                else text_chunk
                            )
                            self.ui.dialog_input.delete("1.0", tk.END)
                            self.ui.dialog_input.insert("1.0", new_text.strip())
                    else:
                        # 直接設置文字
                        self.ui.dialog_input.delete("1.0", tk.END)
                        self.ui.dialog_input.insert("1.0", text_chunk)

                    # 滾動到底部
                    self.ui.dialog_input.see(tk.END)

                    # 更新狀態顯示
                    self._voice_streaming_dots = (self._voice_streaming_dots + 1) % 4
                    dots = "." * self._voice_streaming_dots

        # 在主線程中更新
        self.root.after(0, update_ui)

    def _find_text_overlap(self, text1: str, text2: str) -> str:
        """查找兩個文字之間的重疊部分（簡單實現）"""
        if not text1 or not text2:
            return ""

        # 簡單實現：檢查結尾和開頭的重疊
        min_len = min(len(text1), len(text2))
        for i in range(min_len, 0, -1):
            if text1.endswith(text2[:i]):
                return text2[:i]
        return ""

    def _use_legacy_voice_recognition(self, timestamp):
        """使用舊版語音識別（兼容模式）"""

        def recognize_and_update():
            try:
                recognized_text = self.voice_recognition.recognize_speech()

                if recognized_text:
                    # 將識別結果附加到輸入框（不清空原有內容）
                    self.ui.append_to_dialog_input(recognized_text, True, True)

                self._is_voice_streaming = False

            except Exception as e:
                error_msg = f"語音識別失敗: {str(e)}"
                self.logger.error(error_msg)
                self._is_voice_streaming = False

        # 在後台線程中進行識別
        threading.Thread(target=recognize_and_update, daemon=True).start()

    def run(self):
        """運行應用程式"""
        try:
            self.logger.info("啟動 WofaRunner 應用程式 app")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("收到中斷信號，正在關閉...")
        finally:
            self.running = False
            self.cleanup()

    def cleanup(self):
        """清理資源"""
        self.logger.info("正在清理資源...")
        try:
            self.running = False
            # 停止异步事件循环
            if hasattr(self, "async_loop"):
                self.async_loop.stop()
                # 清理其他资源
            if hasattr(self, "voice_tts"):
                self.voice_tts.cleanup()

            if hasattr(self, "voice_recognition"):
                self.voice_recognition.cleanup()

            if hasattr(self, "wofa_service"):
                self.wofa_service.cleanup()

            if hasattr(self, "main_window"):
                self.ui.cleanup()

        except Exception as e:
            self.logger.error(f"清理資源時出錯: {e}")
        self.logger.info("WofaRunner 應用程式已關閉")
