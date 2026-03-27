@echo off
echo "Building main application with python..."
rem pyinstaller wofa_ide.spec
uv run python build.py

if %errorlevel% neq 0 (
    echo "Error: Main application build failed!"
    exit /b 1
)

echo "Building installer..."
python build_installer.py

if %errorlevel% neq 0 (
    echo "Error: Installer build failed!"
    exit /b 1
)

echo "Build completed successfully!"