@echo off
REM 双击这个文件即可启动程序（Windows）。
REM 首次运行会自动创建虚拟环境并安装依赖，可能需要1-2分钟，请耐心等待。

cd /d "%~dp0"

if not exist venv (
    echo ============================================================
    echo  首次运行，正在创建运行环境并安装依赖，请稍候（1-2分钟）...
    echo ============================================================
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>&1
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo ============================================================
echo  正在启动量化策略控制台，浏览器会自动打开...
echo  如需停止程序，直接关闭这个窗口即可。
echo ============================================================
echo.

python main.py

pause
