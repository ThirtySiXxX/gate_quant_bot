#!/bin/bash
# 发布新版本。用法：
#     ./scripts/release.sh 1.0.0
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
[ -n "$NEW_VERSION" ] || die "用法: ./scripts/release.sh <版本号>   例如 ./scripts/release.sh 1.0.0"
NEW_VERSION="${NEW_VERSION#v}"

# ---------- 1. 版本号 ----------
echo "${YLW}[1/6]${RST} 检查版本号"
[[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
  || die "版本号必须是 主版本.次版本.修订号 的形式（如 1.0.0），你给的是：$NEW_VERSION"

CUR_VERSION="$(cat VERSION 2>/dev/null | tr -d '[:space:]')"
[ -n "$CUR_VERSION" ] || die "读不到 VERSION 文件"

# 用 sort -V 做语义化版本比较，避免 1.10.0 被当成小于 1.9.0
NEWEST="$(printf '%s\n%s\n' "$CUR_VERSION" "$NEW_VERSION" | sort -V | tail -1)"
[ "$NEWEST" = "$NEW_VERSION" ] && [ "$CUR_VERSION" != "$NEW_VERSION" ] \
  || die "新版本号必须大于当前版本。当前 $CUR_VERSION，你给的 $NEW_VERSION"
ok "版本号 $CUR_VERSION → $NEW_VERSION"

# ---------- 2. CHANGELOG ----------
echo "${YLW}[2/6]${RST} 检查 CHANGELOG"
# 客户端靠"## 开头且包含版本号"的行来定位章节，这里用同样的规则校验
grep -q "^##.*${NEW_VERSION}" CHANGELOG.md \
  || die "CHANGELOG.md 里找不到 $NEW_VERSION 的章节。
     请先加一节，标题格式必须是：
         ## ${NEW_VERSION} — $(date +%Y-%m-%d)
     用户在「检查更新」页看到的更新说明就是这一节的内容，不写用户就不知道改了什么。"

SECTION_LINES="$(awk -v v="$NEW_VERSION" '
  $0 ~ "^##.*"v {f=1; next}
  f && /^## / {exit}
  f {print}
' CHANGELOG.md | grep -c '[^[:space:]]' || true)"
[ "$SECTION_LINES" -ge 2 ] || die "CHANGELOG 里 $NEW_VERSION 那节几乎是空的（只有 $SECTION_LINES 行有内容），请补充说明"
ok "CHANGELOG 已写 $NEW_VERSION（$SECTION_LINES 行）"

# ---------- 3. git 状态 ----------
echo "${YLW}[3/6]${RST} 检查 git 状态"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "当前目录不是 git 仓库"

# 清理沙箱/异常退出留下的锁文件，否则后面每一步都会被挡住
find .git -name '*.lock' -delete 2>/dev/null || true

[ -z "$(git status --porcelain | grep -v '^?? ' || true)" ] \
  || { git status --short; die "有未提交的改动，请先提交或 stash"; }

BRANCH="$(git branch --show-current)"
[ "$BRANCH" = "main" ] || echo "${YLW}⚠${RST}  当前在 $BRANCH 分支而不是 main，确认无误再继续"

git rev-parse "v$NEW_VERSION" >/dev/null 2>&1 \
  && die "标签 v$NEW_VERSION 已存在。删除旧标签：git tag -d v$NEW_VERSION && git push origin :v$NEW_VERSION"

if git remote get-url origin >/dev/null 2>&1; then
  git fetch --quiet origin "$BRANCH" 2>/dev/null || true
  BEHIND="$(git rev-list --count "HEAD..origin/$BRANCH" 2>/dev/null || echo 0)"
  [ "$BEHIND" = "0" ] || die "本地落后远端 $BEHIND 个提交，请先 git pull"
fi
ok "工作区干净，标签可用"

# ---------- 4. 测试 ----------
echo "${YLW}[4/6]${RST} 跑测试"
PY=python3
[ -x "venv/bin/python" ] && PY="venv/bin/python"
[ -x "venv/Scripts/python.exe" ] && PY="venv/Scripts/python.exe"
"$PY" -m unittest discover -s tests -q || die "测试没过，中止发布"
"$PY" -m compileall -q src main.py >/dev/null || die "有语法错误，中止发布"
ok "测试通过"

# ---------- 5. 写版本并提交 ----------
echo "${YLW}[5/6]${RST} 写入版本号并提交"
echo "$NEW_VERSION" > VERSION
git add VERSION CHANGELOG.md
git commit -q -m "发布 v$NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "v$NEW_VERSION"
ok "已提交并打标签 v$NEW_VERSION"

# ---------- 6. 推送 ----------
echo "${YLW}[6/6]${RST} 推送到远端"
if git remote get-url origin >/dev/null 2>&1; then
  read -r -p "  确认推送 $BRANCH 和标签 v$NEW_VERSION 到 origin？(y/N) " ans
  case "$ans" in
    [yY]*)
      git push origin "$BRANCH"
      git push origin "v$NEW_VERSION"
      ok "已推送"
      SLUG="$(git remote get-url origin | sed -E 's#.*github\.com[:/]+([^/]+/[^/]+?)(\.git)?$#\1#')"
      echo
      echo "${GRN}发布完成：v$NEW_VERSION${RST}"
      echo
      echo "  用户端此刻已经能检测到更新了（客户端读仓库里的 VERSION 文件）。"
      echo
      echo "  ${DIM}可选：再建一个 GitHub Release，用户就能直接下载 zip：${RST}"
      echo "    https://github.com/$SLUG/releases/new?tag=v$NEW_VERSION"
      echo "    ${DIM}标题填 v$NEW_VERSION，正文把 CHANGELOG 里这一节粘进去${RST}"
      ;;
    *)
      echo "  已跳过推送。稍后手动执行："
      echo "    git push origin $BRANCH && git push origin v$NEW_VERSION"
      ;;
  esac
else
  echo "  没有配置 origin 远端，跳过推送。"
fi
