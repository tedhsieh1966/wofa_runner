"""
SmartPal 配置管理模組
處理應用程式設定和配置
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, cast


class WfaManager:
    def __init__(
        self, wfa_filename: Optional[str] = None, wfa_path_str: Optional[str] = None
    ):
        import logging

        self._logger = logging.getLogger("WfaManager")

        if wfa_path_str:
            self.wfa_path_str = wfa_path_str
        else:
            if wfa_filename:
                self.wfa_path_str = self.get_wfa_path_str(wfa_filename)
            elif len(sys.argv) > 1:
                arg = sys.argv[1]
                if os.path.isabs(arg):
                    # 完整路徑，直接使用
                    self.wfa_path_str = arg
                else:
                    # 只有檔名，透過 get_wfa_path_str 補上路徑
                    self.wfa_path_str = self.get_wfa_path_str(arg)

        self._logger.info(f"WfaManager __init__ wfa_path_str={wfa_path_str}")
        if self.wfa_path_str:
            self.wfa = self.load_wfa()

    def load_wfa(self) -> Dict[str, Any]:
        """加載配置"""
        if self.wfa_path_str:
            try:
                with open(self.wfa_path_str, "r", encoding="utf-8") as f:
                    wfa = json.load(f)
                    # 深度合併配置
                    return wfa
            except Exception as e:
                self._logger.warning(f"加載配置失敗，使用默認配置: {e}")

        return None

    def get_wfa_str(self):
        return json.dumps(self.wfa)

    def get_wfa_path_str(self, filename: str):
        if getattr(sys, "frozen", False):
            project_root = os.path.dirname(sys.executable)  # 打包后：exe所在文件夹
        else:
            project_root = str(
                Path(__file__).resolve().parent.parent
            )  # 开发时：脚本所在文件夹

        return f"{project_root}/wofa/{filename}"
