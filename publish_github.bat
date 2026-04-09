@echo off
setlocal
echo ============================================================
echo  Publish wofa_runner to GitHub
echo ============================================================
echo.
echo This script:
echo   1. Temporarily replaces pyproject.toml with pyproject.toml.github
echo   2. Commits + pushes to GitHub
echo   3. Restores your local pyproject.toml
echo.

:: Safety check — make sure pyproject.toml.github exists
if not exist pyproject.toml.github (
    echo ERROR: pyproject.toml.github not found.
    exit /b 1
)

:: Safety check — warn if there are uncommitted source changes
git diff --quiet
if %errorlevel% neq 0 (
    echo WARNING: You have unstaged changes. Consider committing them first.
    echo Press Ctrl+C to abort, or any key to continue anyway...
    pause >nul
)

:: ---- Swap in the github pyproject.toml ----
echo [1/4] Swapping in pyproject.toml.github...
copy /y pyproject.toml pyproject.toml.local >nul

copy /y pyproject.toml.github pyproject.toml >nul

:: ---- Stage ALL changes (source + the swapped pyproject.toml) ----
echo [2/4] Staging changes...
git add .

:: ---- Commit ----
echo [3/4] Committing and pushing...
git diff --cached --quiet
if %errorlevel% equ 0 (
    echo   Nothing new to commit.
) else (
    set /p COMMIT_MSG="Commit message (leave blank for default): "
    if "%COMMIT_MSG%"=="" set COMMIT_MSG=chore: publish release
    git commit -m "%COMMIT_MSG%"
)
git push origin master
if %errorlevel% neq 0 (
    echo ERROR: git push failed. Restoring local pyproject.toml...
    copy /y pyproject.toml.local pyproject.toml >nul
    del pyproject.toml.local >nul
    exit /b 1
)

:: ---- Restore local pyproject.toml ----
echo [4/4] Restoring local pyproject.toml...
copy /y pyproject.toml.local pyproject.toml >nul
del pyproject.toml.local >nul

:: Tell git to ignore the local pyproject.toml diff (it differs from what was pushed)
git update-index --assume-unchanged pyproject.toml

echo.
echo ============================================================
echo  Done! Published to GitHub.
echo  Local pyproject.toml is restored.
echo.
echo  NOTE: git status may still show pyproject.toml as clean
echo  because of --assume-unchanged. To re-enable tracking:
echo    git update-index --no-assume-unchanged pyproject.toml
echo ============================================================