"""
WofaRunner CLI 應用程式
使用 stdin/stdout 執行 .wfa 工作流程，無需 GUI。
"""

import asyncio
import logging
import queue
import sys
import threading
from pathlib import Path
from typing import Any, Optional

current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from wofa_server.wofa_service import (
    LABEL_LLM_REPLY,
    LABEL_STD_OUTPUT,
    LABEL_WAIT_USER_INPUT,
    WofaService,
)

from wfa_manager import WfaManager

TEMP_DIR_BASE = "c:/temp"
EOS_PATTERN = "END_OF_STREAMING"


class _AsyncEventLoop:
    """在背景執行緒中執行 asyncio event loop。"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("CliAsyncEventLoop")
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self.running = False

    def start(self):
        if self.running:
            return

        def run_loop():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.running = True
            self._ready.set()
            try:
                self.loop.run_forever()
            finally:
                self.running = False

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()
        self._ready.wait()

    def stop(self):
        if self.loop and self.running:
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.running = False

    def run_coroutine(self, coroutine):
        if not self.loop or not self.running:
            return None
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)


class WofaRunnerCliApp:
    """
    CLI 模式的 WofaRunner。
    - 工作流程在背景執行緒執行
    - LLM 回應與 std_output 寫到 stdout
    - 需要使用者輸入時，提示寫到 stderr，從 stdin 讀一行
    """

    def __init__(self, wfa_path_str: Optional[str] = None):
        self.logger = logging.getLogger("WofaRunner.Cli")

        self.wfa_mgr = WfaManager(wfa_path_str=wfa_path_str)
        if not self.wfa_mgr.wfa_path_str or self.wfa_mgr.wfa is None:
            raise FileNotFoundError(
                f"無法載入 .wfa 檔案: {self.wfa_mgr.wfa_path_str!r}"
            )

        self.eos_pattern = EOS_PATTERN
        self._stream_tail = ""
        self._is_eos = False
        self._stream_lock = threading.Lock()

        self._input_requests: "queue.Queue[tuple[Optional[str], Any]]" = queue.Queue()
        self._workflow_done = threading.Event()

        self.async_loop = _AsyncEventLoop(self.logger)
        self.wofa_service = WofaService(
            temp_dir_base=TEMP_DIR_BASE,
            callback=self._on_wofa_response,
        )

    # ---------- WofaService 回呼（在工作流程執行緒中） ----------

    def _on_wofa_response(
        self,
        tag: str,
        task_id: str,
        status: str,
        response: dict,
        node: Optional[Any] = None,
    ):
        try:
            if tag == LABEL_LLM_REPLY:
                streaming = response.get("llm_reply_streaming", "")
                final = response.get("llm_reply", "")
                if status in ("completed", "streaming"):
                    if streaming:
                        self._write_llm_stream(streaming)
                    if final:
                        self._write_llm_stream(final)
                if status == "completed":
                    self._finish_llm_stream()
                    self.wofa_service.finish_task(task_id)
                elif status == "error":
                    sys.stderr.write(f"\n[error] {final or streaming}\n")
                    sys.stderr.flush()
                    self.wofa_service.finish_task(task_id)

            elif tag == LABEL_STD_OUTPUT:
                self._write_std_output(response.get("std_output"))

            elif tag == LABEL_WAIT_USER_INPUT:
                self._input_requests.put((response.get("prompt"), node))

        except Exception as e:
            self.logger.error(f"處理 WofaService 回應時出錯: {e}")

    # ---------- 串流輸出處理 ----------

    def _write_llm_stream(self, chunk: str):
        """過濾 EOS 標記並把可安全輸出的部分寫到 stdout。"""
        with self._stream_lock:
            if self._is_eos or not chunk:
                return
            self._stream_tail += chunk
            idx = self._stream_tail.find(self.eos_pattern)
            if idx >= 0:
                emit = self._stream_tail[:idx]
                self._stream_tail = ""
                self._is_eos = True
                if emit:
                    sys.stdout.write(emit)
                    sys.stdout.flush()
                return
            keep = len(self.eos_pattern) - 1
            if len(self._stream_tail) > keep:
                emit = self._stream_tail[:-keep]
                self._stream_tail = self._stream_tail[-keep:]
                sys.stdout.write(emit)
                sys.stdout.flush()

    def _finish_llm_stream(self):
        with self._stream_lock:
            if not self._is_eos and self._stream_tail:
                sys.stdout.write(self._stream_tail)
            self._stream_tail = ""
            self._is_eos = False
            sys.stdout.write("\n")
            sys.stdout.flush()

    def _write_std_output(self, std_output: Any):
        if isinstance(std_output, dict):
            text = std_output.get("text", "")
        elif isinstance(std_output, str):
            text = std_output
        else:
            text = "" if std_output is None else str(std_output)
        if not text:
            return
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()

    # ---------- 工作流程啟動 ----------

    async def _start_workflow(self):
        try:
            project_file_content = self.wfa_mgr.get_wfa_str()
            await self.wofa_service.start_workflow_async(
                project_file_content=project_file_content,
            )
        except Exception as e:
            self.logger.error(f"啟動工作流程失敗: {e}")
            sys.stderr.write(f"[error] 工作流程失敗: {e}\n")
            sys.stderr.flush()
        finally:
            self._workflow_done.set()

    # ---------- 主迴圈 ----------

    def run(self) -> int:
        self.async_loop.start()
        future = self.async_loop.run_coroutine(self._start_workflow())
        if future is None:
            sys.stderr.write("[error] 無法啟動 asyncio 事件迴圈\n")
            return 1

        exit_code = 0
        try:
            while not self._workflow_done.is_set():
                try:
                    prompt, node = self._input_requests.get(timeout=0.2)
                except queue.Empty:
                    continue

                if prompt:
                    sys.stderr.write(prompt)
                    if not prompt.endswith("\n"):
                        sys.stderr.write("\n")
                    sys.stderr.flush()

                line = sys.stdin.readline()
                if not line:
                    user_input = ""
                else:
                    user_input = line.rstrip("\r\n")

                if node is not None:
                    node.on_user_input_received(user_input)

            # 等工作流程協程結束
            try:
                future.result(timeout=5)
            except Exception:
                pass

        except KeyboardInterrupt:
            sys.stderr.write("\n[interrupted]\n")
            exit_code = 130
        finally:
            self._cleanup()

        return exit_code

    def _cleanup(self):
        try:
            if hasattr(self.wofa_service, "cleanup"):
                self.wofa_service.cleanup()
        except Exception as e:
            self.logger.error(f"清理 WofaService 時出錯: {e}")
        try:
            self.async_loop.stop()
        except Exception:
            pass