#!/bin/bash
# 发布新版本。用法：
#     ./scripts/release.sh 1.0.1 --check   # 只检查
#     ./scripts/release.sh 1.0.1           # 正式发布
#
# 这个脚本把"发版容易忘的事"全部做成强制检查，任何一步不过就中止：
#   - 版本号格式对不对、是不是真的比当前版本新
#   - CHANGELOG.md 里有没有写这个版本的说明（用户更新时看到的就是它）
#   - 工作区干不干净、在不在主分支、和远端有没有分叉
#   - 测试过不过
# 通过之后才写 VERSION、提交、打标签、推送。

set -euo pipefail
cd "$(dirname "$0")/.."

RED=$'\033[31m'; GRN=$'\033[32m'; YLW=$'\033[33m'; DIM=$'\033[2m'; RST=$'\033[0m'
die() { echo "${RED}✘ $*${RST}" >&2; exit 1; }
ok()  { echo "${GRN}✔${RST} $*"; }
info(){ echo "${DIM}  $*${RST}"; }

NEW_VERSION="${1:-}"
[ -n "$NEW_VERSION" ] || die "用法: ./scripts/release.sh <版本号> [--check]   例如 ./scripts/release.sh 1.0.1 --check"
NEW_VERSION="${NEW_VERSION#v}"
CHECK_ONLY=false
[ "${2:-}" = "--check" ] && CHECK_ONLY=true
[ -z "${2:-}" ] || [ "${2:-}" = "--check" ] || die "不支持的参数：${2:-}"

PY=python3
[ -x "venv/bin/python" ] && PY="venv/bin/python"
[ -x "venv/Scripts/python.exe" ] && PY="venv/Scripts/python.exe"

# ---------- 1. 版本号 ----------
echo "${YLW}[1/6]${RST} 检查版本号"
[[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || die "版本号必须是 主版本.次版本.修订号 的形式（如 1.0.0），你给的是：$NEW_VERSION"

CUR_VERSION="$(cat VERSION 2>/dev/null | tr -d '[:space:]')"
[ -n "$CUR_VERSION" ] || die "读不到 VERSION 文件"

# 用 Python 数字元组比较，兼容 macOS / Linux / Windows Git Bash。
"$PY" -c 'import sys; a=tuple(map(int,sys.argv[1].split("."))); b=tuple(map(int,sys.argv[2].split("."))); raise SystemExit(0 if b>a else 1)' \
  "$CUR_VERSION" "$NEW_VERSION" \
  || die "新版本号必须大于当前版本。当前 $CUR_VERSION，你给的 $NEW_VERSION"
ok "版本号 $CUR_VERSION → $NEW_VERSION"

# ---------- 2. CHANGELOG ----------
echo "${YLW}[2/6]${RST} 检查 CHANGELOG"
# 客户端靠"## 开头且包含版本号"的行来定位章节，这里用同样的规则校验
awk -v v="$NEW_VERSION" '$1 == "##" { h=$2; sub(/^v/, "", h); if (h == v) found=1 } END { exit !found }' CHANGELOG.md \
  || die "CHANGELOG.md 里找不到 $NEW_VERSION 的章节。
     请先加一节，标题格式必须是：
         ## ${NEW_VERSION} — $(date +%Y-%m-%d)
     用户在「检查更新」页看到的更新说明就是这一节的内容，不写用户就不知道改了什么。"

SECTION_LINES="$(awk -v v="$NEW_VERSION" '
  $1 == "##" {
    h=$2; sub(/^v/, "", h)
    if (f) exit
    if (h == v) {f=1; next}
  }
  f {print}
' CHANGELOG.md | grep -c '[^[:space:]]' || true)"
[ "$SECTION_LINES" -ge 2 ] || die "CHANGELOG 里 $NEW_VERSION 那节几乎是空的（只有 $SECTION_LINES 行有内容），请补充说明"
ok "CHANGELOG 已写 $NEW_VERSION（$SECTION_LINES 行）"

# ---------- 3. git 状态 ----------
echo "${YLW}[3/6]${RST} 检查 git 状态"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "当前目录不是 git 仓库"

# CHANGELOG 可以是本次待发布改动；其余已跟踪或未跟踪文件一律阻断，避免漏发。
UNEXPECTED="$(git status --porcelain | awk 'substr($0,4) != "CHANGELOG.md" {print}')"
[ -z "$UNEXPECTED" ] \
  || { git status --short; die "除 CHANGELOG.md 外还有未提交或未跟踪的改动，请先处理"; }

BRANCH="$(git branch --show-current)"
[ "$BRANCH" = "main" ] || die "正式发布必须在 main 分支执行；当前是 $BRANCH"

git remote get-url origin >/dev/null 2>&1 || die "没有配置 origin，无法执行正式发布"
git fetch --quiet --tags origin "$BRANCH" || die "无法刷新 origin/$BRANCH；未确认远端状态，已中止"
git rev-parse "v$NEW_VERSION" >/dev/null 2>&1 \
  && die "标签 v$NEW_VERSION 已存在。请改用更高版本号；不要覆盖已经发布的标签"
BEHIND="$(git rev-list --count "HEAD..origin/$BRANCH" 2>/dev/null || echo 0)"
[ "$BEHIND" = "0" ] || die "本地落后远端 $BEHIND 个提交，请先 git pull"
ok "发布改动范围正确，标签可用，远端状态已确认"

# ---------- 4. 测试 ----------
echo "${YLW}[4/6]${RST} 跑测试"
"$PY" -m unittest discover -s tests -q || die "测试没过，中止发布"
"$PY" -m compileall -q src main.py >/dev/null || die "有语法错误，中止发布"
ok "测试通过"

if $CHECK_ONLY; then
  echo
  ok "发布前检查全部通过；没有修改版本号、提交、标签或远端"
  exit 0
fi

# ---------- 5. 写版本并提交 ----------
echo "${YLW}[5/6]${RST} 写入版本号并提交"
read -r -p "  确认创建 v$NEW_VERSION 发布提交和标签，并推送到 origin？(y/N) " ans
case "$ans" in
  [yY]*) ;;
  *) echo "  已取消；未修改 VERSION、提交或标签。"; exit 0 ;;
esac
echo "$NEW_VERSION" > VERSION
git add -- VERSION CHANGELOG.md
git commit -q -m "发布 v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "v$NEW_VERSION"
ok "已提交并打标签 v$NEW_VERSION"

# ---------- 6. 推送 ----------
echo "${YLW}[6/6]${RST} 推送到远端"
git push --atomic origin "$BRANCH" "v$NEW_VERSION"
ok "已原子推送分支与标签"
SLUG="$(git remote get-url origin | sed -E 's#.*github\.com[:/]+([^/]+/[^/]+?)(\.git)?$#\1#')"
echo
echo "${GRN}发布完成：v$NEW_VERSION${RST}"
echo
echo "  用户端此刻已经能检测到更新了（客户端读仓库里的 VERSION 文件）。"
echo
echo "  ${DIM}可选：再建一个 GitHub Release，用户就能直接下载 zip：${RST}"
echo "    https://github.com/$SLUG/releases/new?tag=v$NEW_VERSION"
echo "    ${DIM}标题填 v$NEW_VERSION，正文把 CHANGELOG 里这一节粘进去${RST}"
