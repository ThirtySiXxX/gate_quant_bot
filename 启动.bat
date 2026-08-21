@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Gate.io 量化策略控制台
cd /d "%~dp0"

REM ============================================================
REM  双击即可启动。首次运行会自动准备环境。
REM  如果本机没有 Python，脚本会引导你安装（可选自动安装）。
REM ============================================================

set "PYEXE="

REM ---------- 1. 找 Python ----------
REM 优先用 py 启动器（Windows 官方推荐，能避开 Microsoft Store 的假 python）
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=py -3"
    goto :found_python
)

REM 退而求其次找 python.exe，但要排除 Microsoft Store 的占位程序：
REM Win10/11 未装 Python 时输入 python 会打开应用商店，那个假程序在 WindowsApps 目录下
for /f "delims=" %%i in ('where python 2^>nul') do (
    echo %%i | find /i "WindowsApps" >nul
    if errorlevel 1 (
        set "PYEXE=%%i"
        goto :found_python
    )
)

REM ---------- 2. 没找到 Python，引导安装 ----------
echo.
echo ============================================================
echo   没有检测到 Python 环境
echo ============================================================
echo.
echo  这个程序需要 Python 3.10 或更高版本才能运行。
echo.
echo  请选择：
echo    [1] 自动下载并安装 Python 3.12（推荐，约 25MB，需要联网）
echo    [2] 我自己去官网下载安装
echo    [3] 退出
echo.
set /p "CHOICE=请输入 1 / 2 / 3 后回车: "

if "%CHOICE%"=="3" exit /b 0
if "%CHOICE%"=="2" (
    echo.
    echo  正在打开官网下载页...
    echo  安装时请务必勾选最下方的 "Add python.exe to PATH"！
    start "" "https://www.python.org/downloads/windows/"
    echo.
    echo  装好之后，重新双击本文件即可。
    pause
    exit /b 0
)
if not "%CHOICE%"=="1" (
    echo  输入无效，已退出。
    pause
    exit /b 1
)

REM ---- 自动安装分支 ----
set "PYVER=3.12.8"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/python-%PYVER%-amd64.exe"
set "PYINST=%TEMP%\python-%PYVER%-amd64.exe"

echo.
echo  正在下载 Python %PYVER% ...
where curl >nul 2>&1
if errorlevel 1 (
    powershell -NoProfile -Command "try{[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PYINST%'}catch{exit 1}"
) else (
    curl -L -o "%PYINST%" "%PYURL%"
)
if errorlevel 1 goto :download_failed
if not exist "%PYINST%" goto :download_failed

echo.
echo  正在安装（只装给当前用户，不需要管理员权限）...
echo  这一步大约需要 1-2 分钟，期间可能没有任何进度显示，请勿关闭窗口。
"%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_test=0
if errorlevel 1 (
    echo.
    echo  [错误] 安装程序返回失败。请改用方式 [2] 手动安装。
    pause
    exit /b 1
)
del /q "%PYINST%" >nul 2>&1

REM 刚装完，当前命令行窗口的 PATH 还没刷新，直接用已知的安装路径
set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "!PYEXE!" (
    py -3 --version >nul 2>&1
    if not errorlevel 1 (
        set "PYEXE=py -3"
    ) else (
        echo.
        echo  Python 已安装，但当前窗口还认不到它。
        echo  请关闭这个窗口，然后重新双击本文件即可。
        pause
        exit /b 0
    )
)
echo  Python 安装完成。
goto :found_python

:download_failed
echo.
echo  [错误] 下载失败，可能是网络问题或公司网络限制。
echo  请改用方式 [2]，手动去官网下载安装（记得勾选 Add python.exe to PATH）。
echo  官网: https://www.python.org/downloads/windows/
pause
exit /b 1

:found_python
echo.
for /f "tokens=*" %%v in ('%PYEXE% --version 2^>^&1') do echo  使用 %%v

REM ---------- 3. 准备虚拟环境和依赖 ----------
REM 用标记文件判断依赖是否装完整。只看 venv 目录存在与否是不够的：
REM 如果上次装到一半失败（断网/代理），目录已经建好了，下次就会跳过安装，
REM 结果永远卡在 ImportError 上，而且用户完全不知道为什么。
if exist "venv\.deps_ok" goto :run

if not exist "venv" (
    echo.
    echo  首次运行，正在创建运行环境...
    %PYEXE% -m venv venv
    if errorlevel 1 (
        echo  [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
)

echo.
echo ============================================================
echo   正在安装依赖，需要 1-2 分钟，请耐心等待...
echo ============================================================
call "venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ============================================================
    echo   [错误] 依赖安装失败
    echo ============================================================
    echo  常见原因：网络不通、公司代理拦截、或 PyPI 访问受限。
    echo  可以试试用国内镜像源重装：
    echo.
    echo    venv\Scripts\activate.bat
    echo    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo.
    pause
    exit /b 1
)
echo ok> "venv\.deps_ok"
echo.
echo  依赖安装完成。

:run
call "venv\Scripts\activate.bat"
echo.
echo ============================================================
echo   正在启动量化策略控制台，浏览器会自动打开...
echo   如需停止程序，直接关闭这个窗口即可。
echo ============================================================
echo.
python main.py

echo.
echo  程序已退出。
pause
