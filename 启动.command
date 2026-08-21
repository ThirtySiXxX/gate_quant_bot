#!/bin/bash
# 双击这个文件即可启动程序（macOS）。
# 首次运行会自动创建虚拟环境并安装依赖，可能需要1-2分钟；之后每次双击秒开。

cd "$(dirname "$0")" || exit 1

# ---------- 1. 找 Python ----------
PYEXE=""
for candidate in python3.12 python3.11 python3; do
  if command -v "$candidate" >/dev/null 2>&1; then
    ver=$("$candidate" -c 'import sys; print("%d%d" % sys.version_info[:2])' 2>/dev/null)
    if [ -n "$ver" ] && [ "$ver" -ge 310 ] 2>/dev/null; then
      PYEXE="$candidate"
      break
    fi
  fi
done

if [ -z "$PYEXE" ]; then
  echo ""
  echo "============================================================"
  echo "  没有检测到 Python 3.10+"
  echo "============================================================"
  echo ""
  echo "  这个程序需要 Python 3.10 或更高版本。"
  echo ""
  if command -v brew >/dev/null 2>&1; then
    echo "  检测到你装了 Homebrew，可以直接运行："
    echo ""
    echo "      brew install python@3.12"
    echo ""
    read -r -p "  要现在自动安装吗？(y/N) " ans
    case "$ans" in
      [yY]*)
        brew install python@3.12 || { echo "  安装失败，请手动处理。"; read -r -p "按回车关闭..."; exit 1; }
        PYEXE="$(brew --prefix)/bin/python3.12"
        ;;
      *)
        echo "  已取消。装好后重新双击本文件即可。"
        read -r -p "按回车关闭..."
        exit 0
        ;;
    esac
  else
    echo "  请从官网下载安装： https://www.python.org/downloads/macos/"
    echo "  装好后重新双击本文件即可。"
    open "https://www.python.org/downloads/macos/" 2>/dev/null
    read -r -p "按回车关闭..."
    exit 0
  fi
fi

echo ""
echo " 使用 $($PYEXE --version 2>&1)"

# ---------- 2. 准备虚拟环境和依赖 ----------
# 用标记文件判断依赖是否装完整。只看 venv 目录存在与否是不够的：
# 如果上次装到一半失败（断网/代理），目录已经建好了，下次就会跳过安装，
# 结果永远卡在 ImportError 上，而且完全看不出原因。
if [ ! -f "venv/.deps_ok" ]; then
  if [ ! -d "venv" ]; then
    echo ""
    echo " 首次运行，正在创建运行环境..."
    "$PYEXE" -m venv venv || { echo " [错误] 创建虚拟环境失败。"; read -r -p "按回车关闭..."; exit 1; }
  fi

  echo ""
  echo "============================================================"
  echo "  正在安装依赖，需要 1-2 分钟，请耐心等待..."
  echo "============================================================"
  # shellcheck disable=SC1091
  source venv/bin/activate
  python -m pip install --upgrade pip >/dev/null 2>&1
  if ! python -m pip install -r requirements.txt; then
    echo ""
    echo "============================================================"
    echo "  [错误] 依赖安装失败"
    echo "============================================================"
    echo "  常见原因：网络不通、代理拦截、或 PyPI 访问受限。"
    echo "  可以试试用国内镜像源重装："
    echo ""
    echo "    source venv/bin/activate"
    echo "    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple"
    echo ""
    read -r -p "按回车关闭..."
    exit 1
  fi
  touch "venv/.deps_ok"
  echo ""
  echo " 依赖安装完成。"
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo ""
echo "============================================================"
echo "  正在启动量化策略控制台，浏览器会自动打开..."
echo "  如需停止程序，直接关闭这个终端窗口即可。"
echo "============================================================"
echo ""

python main.py

echo ""
read -r -p "程序已退出，按回车关闭此窗口..."
