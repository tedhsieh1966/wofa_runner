import platform
from pathlib import Path


ROOT_DIR = str(Path(__file__).parent) # __file__ 指到 app_info.py

PROJECTS_DIR = Path(__file__).resolve().parent.parent.parent  # 根据实际层级调整
LIBRARY_PYTHON_DIR = PROJECTS_DIR / "Library" / "python"
PY_LIBRARIES_PYD_DIR = LIBRARY_PYTHON_DIR / "py_libraries" / "src" / "pyd"
PY_LLM_API_PYD_DIR = LIBRARY_PYTHON_DIR / "py_llm_api" / "src" / "pyd"
PY_WORKFLOW_PYD_DIR = LIBRARY_PYTHON_DIR / "py_workflow" / "src" / "pyd"
WOFA_IDE_PYD_DIR = PROJECTS_DIR/"python" / "wofa_ide" / "src" / "pyd"
WOFA_SERVER_PYD_DIR = PROJECTS_DIR/"python" / "wofa_server" / "src" / "pyd"

IS_LITE = False
BRIEF = "SmartPal"
DESCRIPTION = "使用LLM的智慧助手"
APP_CAPS = "SmartPal"
APP = "smartpal"
APP_DESKTOP_LINK = APP_CAPS + ".lnk"
APP_WIN = APP if not IS_LITE else APP + "_lite"
APP_MAC = APP + "_mac" if not IS_LITE else APP + "_mac_lite"
APP_LINUX = APP + "_linux" if not IS_LITE else APP + "_linux_lite"

APP_WIN_EXE = APP_WIN + ".exe"
APP_MAC_EXE = APP_MAC + ".app"
APP_LINUX_EXE = APP_LINUX  # Linux 可執行檔通常沒有副檔名

APP_ICON_WIN = "favicon.ico"
APP_ICON_MAC = "favicon.icns"
APP_ICON_LINUX = "favicon.png"  # Linux 通常使用 PNG 或 SVG

LANGUAGES = "languages.xlsx"
DIR_DIST = "dist"
DIR_BUILD = "build"

# 跨平台配置
system = platform.system()
print("system=", system)
if system == 'Windows':
    SEPARATOR = ';'
    APP_NAME = APP_WIN
    APP_EXE = APP_WIN_EXE
    APP_ICON = APP_ICON_WIN
elif system == 'Darwin':  # macOS
    SEPARATOR = ':'
    APP_NAME = APP_MAC
    APP_EXE = APP_MAC_EXE
    APP_ICON = APP_ICON_MAC
else:  # Linux
    SEPARATOR = ':'
    APP_NAME = APP_LINUX
    APP_EXE = APP_LINUX_EXE
    APP_ICON = APP_ICON_LINUX  # Linux 通常使用 PNG

FP_APP_PY = f"{ROOT_DIR}/src/main.py"
FP_APP_ICON = f"{ROOT_DIR}/src/{APP_ICON}"
FP_LANGUAGES = f"{ROOT_DIR}/src/{LANGUAGES}"

