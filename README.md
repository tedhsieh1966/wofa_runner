# WOFA Runner – Wfa 執行器
整合積累經驗，提升企業智慧
Integrate & Accumulate Experiences, Elevate Corporation Intelligence

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)

[中文版](#中文版) | [English Version](#english-version)

---

## 中文版

### 📖 簡介

WOFA Runner 是 WOFA 工作流程自動化平台的**桌面執行器**。它讓您無需開啟完整的 WOFA IDE，即可直接載入並執行 `.wfa` 工作流程檔案。適合將已完成設計的流程部署至終端使用者電腦，或做為日常自動化任務的輕量執行環境。

### ✨ 主要特色

- **輕量執行** – 直接開啟 `.wfa` 檔案並執行，無需 IDE 環境。
- **多語系介面** – 透過 `languages.xlsx` 支援多語言 UI。
- **跨平台支援** – 支援 Windows、macOS 及 Linux。
- **整合私有函式庫** – 內建 `py_libraries`、`py_llm_api`、`py_workflow` 及 `wofa_server`，支援完整的 AI 工作流程節點。

### 🚀 快速開始

#### 系統需求

- Windows 7/10/11（主要支援平台）
- Python 3.11+（若需從原始碼執行）

#### 安裝

從 [Releases](../../releases) 頁面下載 `wfa_runner_win_installer.exe`，雙擊執行並依指示完成安裝。

安裝後將在 `C:\Users\{用戶名}\AppData\Roaming\WFA_RUNNER` 目錄下產生 `wfa_runner.exe` 及 `languages.xlsx`。

#### API 金鑰設定

使用 `setx` 將 API 金鑰永久寫入 Windows 環境變數（設定後需重新開啟終端機或 WFA Runner 才能生效）：

```bat
setx GEMINI_API_KEY "your-gemini-key-here"
setx DEEPSEEK_API_KEY "your-deepseek-key-here"
```

其他支援的 LLM 金鑰可依相同方式設定（如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`XAI_API_KEY` 等）。

#### 開啟工作流程

1. 啟動 WFA Runner。
2. 點擊「開啟」選取 `.wfa` 工作流程檔案。
3. 點擊「執行」開始執行流程。

### 🔧 從原始碼建置（訂閱者）

若您擁有私有函式庫的存取權限，可從原始碼重新編譯。

#### 前置需求

- Python 3.11–3.13（Windows 64-bit）
- Cython（`pip install cython`）
- setuptools、wheel（`pip install setuptools wheel`）
- GitHub Personal Access Token（用於上傳編譯產物）

#### 建置步驟

1. **取得私有函式庫原始碼**（需具備各私有 repo 的存取權限）：
   - `tedhsieh1966/py-libraries`（私有）
   - `tedhsieh1966/py-llm-api`（私有）
   - `tedhsieh1966/py-workflow`（私有）
   - `tedhsieh1966/wofa-server`（私有）

2. **編譯並打包各函式庫**，在每個目錄下執行 `build_whl.bat`：

   ```bat
   set GITHUB_TOKEN=ghp_your_token_here
   cd path\to\py-libraries  &&  build_whl.bat
   cd path\to\py-llm-api    &&  build_whl.bat
   cd path\to\py-workflow   &&  build_whl.bat
   cd path\to\wofa-server   &&  build_whl.bat
   ```

3. **安裝至本地環境**：

   ```bat
   pip install dist_whl\py_libraries-*.whl
   pip install dist_whl\py_llm_api-*.whl
   pip install dist_whl\py_workflow-*.whl
   pip install dist_whl\wofa_server-*.whl
   ```

4. **安裝 wofa_runner 其餘相依套件**：

   ```bat
   pip install -e .
   ```

### 🤝 貢獻

歡迎提交 Issue 或 Pull Request。如有任何建議，可來信聯絡：syntak.tw@msa.hinet.net

### 📄 授權

本專案採用 MIT 授權條款，詳見 LICENSE 文件。

---

## English Version

### 📖 Introduction

WOFA Runner is the **desktop executor** for the WOFA Workflow Automation platform. It lets you load and run `.wfa` workflow files directly, without opening the full WOFA IDE. Ideal for deploying finished workflows to end-user machines or as a lightweight runtime for daily automation tasks.

### ✨ Key Features

- **Lightweight Execution** – Open a `.wfa` file and run it immediately, no IDE required.
- **Multi-language UI** – Supports multiple interface languages via `languages.xlsx`.
- **Cross-platform** – Supports Windows, macOS, and Linux.
- **Private Library Integration** – Ships with `py_libraries`, `py_llm_api`, `py_workflow`, and `wofa_server` for full AI workflow node support.

### 🚀 Quick Start

#### System Requirements

- Windows 7/10/11 (primary supported platform)
- Python 3.11+ (if running from source)

#### Installation

Download `wfa_runner_win_installer.exe` from the [Releases](../../releases) page, double-click, and follow the wizard.

After installation, `wfa_runner.exe` and `languages.xlsx` will be placed in `C:\Users\{username}\AppData\Roaming\WFA_RUNNER`.

#### API Key Setup

Use `setx` to permanently write API keys to Windows environment variables (restart your terminal or WFA Runner after setting):

```bat
setx GEMINI_API_KEY "your-gemini-key-here"
setx DEEPSEEK_API_KEY "your-deepseek-key-here"
```

Other supported LLM keys can be set the same way (e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `XAI_API_KEY`).

#### Running a Workflow

1. Launch WFA Runner.
2. Click **Open** and select a `.wfa` workflow file.
3. Click **Run** to start execution.

### 🔧 Building from Source (Subscribers)

If you have access to the private library repositories, you can recompile from source.

#### Prerequisites

- Python 3.11–3.13 (Windows 64-bit)
- Cython (`pip install cython`)
- setuptools and wheel (`pip install setuptools wheel`)
- GitHub Personal Access Token (for uploading compiled artifacts)

#### Build Steps

1. Clone the private library repositories (access required):
   - `tedhsieh1966/py-libraries` (private)
   - `tedhsieh1966/py-llm-api` (private)
   - `tedhsieh1966/py-workflow` (private)
   - `tedhsieh1966/wofa-server` (private)

2. Compile and package each library by running `build_whl.bat` in each directory:

   ```bat
   set GITHUB_TOKEN=ghp_your_token_here
   cd path\to\py-libraries  &&  build_whl.bat
   cd path\to\py-llm-api    &&  build_whl.bat
   cd path\to\py-workflow   &&  build_whl.bat
   cd path\to\wofa-server   &&  build_whl.bat
   ```

3. Install into your local environment:

   ```bat
   pip install dist_whl\py_libraries-*.whl
   pip install dist_whl\py_llm_api-*.whl
   pip install dist_whl\py_workflow-*.whl
   pip install dist_whl\wofa_server-*.whl
   ```

4. Install remaining wofa_runner dependencies:

   ```bat
   pip install -e .
   ```

### 🤝 Contributing

Issues and pull requests are welcome. For questions or suggestions, contact us at syntak.tw@msa.hinet.net.

### 📄 License

This project is licensed under the MIT License – see the LICENSE file for details.