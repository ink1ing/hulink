@echo off
REM 构建 Windows 可执行程序 (dist\Hulink.exe)
chcp 65001 >nul
cd /d "%~dp0\.."

if not exist venv ( python -m venv venv )
call venv\Scripts\activate.bat
pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --clean --windowed --onefile --name Hulink gui.py

echo.
echo 构建完成: dist\Hulink.exe
pause
