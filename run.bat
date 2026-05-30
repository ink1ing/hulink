@echo off
REM Hulink 启动脚本 (Windows)，对应 start.sh
chcp 65001 >nul
echo 正在启动 Hulink 代理节点订阅链接转换工具...
echo ========================================

if not exist venv (
    echo 虚拟环境不存在，正在创建...
    python -m venv venv
    echo 虚拟环境创建完成
)

call venv\Scripts\activate.bat

python -c "import requests, yaml, rich" 2>nul
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    echo 依赖包安装完成
)

echo 启动程序...
echo.
python main.py

echo.
echo 程序已退出，感谢使用 Hulink!
pause
