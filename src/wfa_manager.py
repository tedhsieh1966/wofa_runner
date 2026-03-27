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
    def __init__(self, wfa_filename: Optional[str]=None, wfa_path_str : Optional[str] = None):
        self.wfa_path_str = wfa_path_str
        if not wfa_path_str and wfa_filename:
            self.wfa_path_str = self.get_wfa_path_str(wfa_filename)

        if self.wfa_path_str:
            self.wfa = self.load_wfa()
    
    def load_wfa(self) -> Dict[str, Any]:
        """加載配置"""
        if self.wfa_path_str:
            try:
                with open(self.wfa_path_str, 'r', encoding='utf-8') as f:
                    wfa = json.load(f)
                    # 深度合併配置
                    return wfa
            except Exception as e:
                print(f"加載配置失敗，使用默認配置: {e}")
        
        return None

    #def modify_wfa_llm(self, config_mgr: ConfigManager):
    #    """修改 wfa 中的 LLM 配置"""
    #    try:
    #        current_llm_api_key = config_mgr.get_current_llm_api_key()
    #        llms_api = config_mgr.get_llms_api()
#
    #        if not llms_api:
    #            print("未找到 LLMS API 配置")
    #            return
#
    #        controller_node_graphic = CONTROLLER_NODE_GRAPHIC.from_dict(self.wfa['controller_node_graphic'])
    #        list_key = controller_node_graphic.get_list_node_key()
#
    #        for key in list_key:
    #            node = controller_node_graphic.get_node_by_key(key)
    #            if node.enum_node in [ENUM_NODE.NODE_ASK_LLM, ENUM_NODE.NODE_CATEGORIZED_BY_LLM]:
    #                # 設置 LLM API key
    #                node.set_llm_api_key(current_llm_api_key)
    #                controller_node_graphic.update_node(node)
#
    #        # 更新 wfa
    #        self.wfa['controller_node_graphic'] = controller_node_graphic.to_dict()
#
    #        # 更新 llms_api - 直接使用 LLMS_API 的 to_dict 方法
    #        self.wfa['llms_api'] = llms_api.to_dict()
#
    #    except Exception as e:
    #        print(f"修改 wfa LLM 配置時出錯: {e}")

    def get_wfa_str(self):
        return json.dumps(self.wfa)

    def get_wfa_path_str(self, filename: str):
        if getattr(sys, 'frozen', False):
            project_root = os.path.dirname(sys.executable)  # 打包后：exe所在文件夹
        else:
            project_root = str(Path(__file__).resolve().parent.parent.parent)  # 开发时：脚本所在文件夹

        return f"{project_root}/wofa/{filename}"
