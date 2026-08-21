"""
版本检查与在线更新。

设计取舍说明（这块很容易做成"看起来能用但会毁掉用户数据"的样子，所以写清楚）：

1. **更新方式按仓库形态自动选择**
   - 如果本地是 git 克隆（存在 .git 且能找到 git 命令）→ 用 `git pull`。
     这是最安全的方式：git 天然不会碰被 .gitignore 忽略的文件，
     也就是说 data/（含 API Key、数据库、K线缓存）和 config.yaml 一定不会被覆盖。
   - 否则（用户是下载 zip 解压的）→ 只做"检测 + 给下载链接"，**不自动覆盖文件**。
     自动解压覆盖看似方便，但一旦路径判断出错就可能删掉用户的密钥和账本，
     这个风险不值得为省一次手动操作去冒。

2. **永远不在有持仓/引擎运行时自动更新**。更新会替换策略代码，
   而引擎可能正持有实盘仓位，中途换代码是危险的。所以更新前必须先停引擎。

3. **检查更新走 GitHub 公开接口，不需要 token**，失败就静默降级，
   绝不能因为更新检查失败而影响交易主流程。
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger("bot.updater")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION_FILE = os.path.join(PROJECT_ROOT, "VERSION")
CHANGELOG_FILE = os.path.join(PROJECT_ROOT, "CHANGELOG.md")
UPDATE_STATE_FILE = os.path.join(PROJECT_ROOT, "data", "update_state.json")

HTTP_TIMEOUT = 8.0


# ============================================================ 版本号
def parse_version(text: str) -> Tuple[int, ...]:
    """把 'v1.2.3' / '1.2.3' 解析成 (1,2,3)。解析不了返回 (0,0,0)，
    这样它一定不会被判定成"更新"，避免因为格式异常给用户推送假更新。"""
    if not text:
        return (0, 0, 0)
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", str(text).strip().lstrip("vV"))
    if not m:
        return (0, 0, 0)
    return tuple(int(x) for x in m.groups())


def current_version() -> str:
    try:
        with open(VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


# ============================================================ 本地状态（跳过的版本等）
def _load_state() -> dict:
    try:
        with open(UPDATE_STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(UPDATE_STATE_FILE), exist_ok=True)
        with open(UPDATE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.warning("保存更新状态失败: %s", e)


def skip_version(version: str) -> None:
    st = _load_state()
    skipped = set(st.get("skipped_versions", []))
    skipped.add(version)
    st["skipped_versions"] = sorted(skipped)
    _save_state(st)


def unskip_all() -> None:
    st = _load_state()
    st["skipped_versions"] = []
    _save_state(st)


def is_skipped(version: str) -> bool:
    return version in set(_load_state().get("skipped_versions", []))


def mark_checked(result: dict) -> None:
    st = _load_state()
    st["last_check_ts"] = time.time()
    st["last_result"] = {k: v for k, v in result.items() if k != "changelog"}
    _save_state(st)


def last_check_ts() -> Optional[float]:
    return _load_state().get("last_check_ts")


# ============================================================ 仓库形态探测
def git_available() -> bool:
    return shutil.which("git") is not None


def is_git_clone() -> bool:
    return os.path.isdir(os.path.join(PROJECT_ROOT, ".git")) and git_available()


def _run_git(args: List[str], timeout: float = 60.0) -> Tuple[bool, str]:
    try:
        p = subprocess.run(["git"] + args, cwd=PROJECT_ROOT, capture_output=True,
                           text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode == 0, out.strip()
    except (subprocess.SubprocessError, OSError) as e:
        return False, str(e)


def detect_repo_slug() -> Optional[str]:
    """从 git remote 自动推断 owner/repo，省得用户手填。"""
    if not is_git_clone():
        return None
    ok, out = _run_git(["remote", "get-url", "origin"], timeout=10)
    if not ok or not out:
        return None
    m = re.search(r"github\.com[:/]+([^/\s]+)/([^/\s]+?)(?:\.git)?$", out.strip().splitlines()[0])
    return f"{m.group(1)}/{m.group(2)}" if m else None


# ============================================================ 远端检查
def _http_get(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": "gate-quant-bot-updater",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError, ValueError) as e:
        logger.info("更新检查请求失败 %s: %s", url, e)
        return None


@dataclass
class UpdateInfo:
    ok: bool = False
    has_update: bool = False
    current: str = ""
    latest: str = ""
    changelog: str = ""
    published_at: str = ""
    html_url: str = ""
    download_url: str = ""
    source: str = ""            # release | raw
    can_auto_update: bool = False
    update_method: str = "manual"   # git | manual
    skipped: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def check_for_update(repo_slug: Optional[str] = None,
                     branch: str = "main") -> UpdateInfo:
    """检查是否有新版本。

    优先读 GitHub Releases（有正式发布时最准），拿不到就退回读仓库里的 VERSION 文件，
    这样即使作者没发 release，只要提交了新的 VERSION 也能检测到。
    """
    cur = current_version()
    info = UpdateInfo(current=cur)

    slug = repo_slug or detect_repo_slug()
    if not slug:
        info.message = ("没有配置仓库地址，也无法从 git remote 自动推断。"
                        "请在下方填写 GitHub 仓库（格式 用户名/仓库名）后再检查。")
        return info

    info.update_method = "git" if is_git_clone() else "manual"
    info.can_auto_update = is_git_clone()

    # ---- 方式1：GitHub Releases ----
    raw = _http_get(f"https://api.github.com/repos/{slug}/releases/latest")
    if raw:
        try:
            d = json.loads(raw)
            tag = d.get("tag_name") or d.get("name") or ""
            if parse_version(tag) > (0, 0, 0):
                info.ok = True
                info.latest = str(tag).lstrip("vV")
                info.changelog = d.get("body") or ""
                info.published_at = d.get("published_at") or ""
                info.html_url = d.get("html_url") or f"https://github.com/{slug}/releases"
                info.download_url = d.get("zipball_url") or f"https://github.com/{slug}/archive/refs/heads/{branch}.zip"
                info.source = "release"
        except (json.JSONDecodeError, AttributeError):
            pass

    # ---- 方式2：直接读仓库里的 VERSION / CHANGELOG ----
    if not info.ok:
        ver_txt = _http_get(f"https://raw.githubusercontent.com/{slug}/{branch}/VERSION")
        if ver_txt and parse_version(ver_txt) > (0, 0, 0):
            info.ok = True
            info.latest = ver_txt.strip().lstrip("vV")
            info.source = "raw"
            info.html_url = f"https://github.com/{slug}"
            info.download_url = f"https://github.com/{slug}/archive/refs/heads/{branch}.zip"
            cl = _http_get(f"https://raw.githubusercontent.com/{slug}/{branch}/CHANGELOG.md")
            if cl:
                info.changelog = extract_changelog_section(cl, info.latest)

    if not info.ok:
        info.message = ("无法连接 GitHub 获取版本信息。可能是网络不通、仓库地址填错，"
                        "或仓库是私有的（私有仓库无法用匿名接口检查）。")
        return info

    info.has_update = is_newer(info.latest, cur)
    info.skipped = is_skipped(info.latest)
    if info.has_update:
        info.message = f"发现新版本 {info.latest}（当前 {cur}）"
    else:
        info.message = f"已是最新版本（{cur}）"
    mark_checked(info.to_dict())
    return info


def extract_changelog_section(text: str, version: str) -> str:
    """从 CHANGELOG.md 里抽出指定版本那一节。抽不到就返回开头一段，
    总比什么都不显示强。"""
    if not text:
        return ""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("## ") and version in ln:
            start = i
            break
    if start is None:
        body = [ln for ln in lines if not ln.startswith("#")][:40]
        return "\n".join(body).strip()
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("## "):
            end = j
            break
    return "\n".join(lines[start:end]).strip()


def local_changelog(version: Optional[str] = None) -> str:
    try:
        with open(CHANGELOG_FILE, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return ""
    return extract_changelog_section(text, version or current_version())


# ============================================================ 执行更新
def perform_update(engine_running: bool, has_positions: bool) -> dict:
    """执行 git pull 更新。

    两道前置检查是刻意的，不要为了"方便"去掉：
      - 引擎在跑 -> 更新会替换正在执行的策略代码
      - 还有持仓 -> 更新后代码行为可能变化，而仓位是真金白银
    """
    steps: List[dict] = []

    def step(name, ok, msg):
        steps.append({"name": name, "ok": ok, "message": msg})

    if engine_running:
        return {"ok": False, "steps": [],
                "message": "引擎正在运行中。请先到仪表盘点「停止引擎」，再执行更新——"
                            "更新会替换策略代码，运行中替换有风险。"}
    if has_positions:
        return {"ok": False, "steps": [],
                "message": "当前还有未平仓的持仓。更新后策略行为可能变化，"
                            "建议先平掉仓位（或确认你清楚风险后手动更新）。"}
    if not is_git_clone():
        return {"ok": False, "steps": [],
                "message": "当前不是 git 克隆的目录，无法自动更新。"
                            "请用下方的下载链接手动下载新版，解压后把 data/ 和 config.yaml "
                            "复制到新目录即可（这两个是你的密钥和配置，务必保留）。"}

    ok, out = _run_git(["status", "--porcelain"], timeout=20)
    if not ok:
        return {"ok": False, "steps": [], "message": f"读取 git 状态失败: {out}"}
    if out.strip():
        changed = [l for l in out.splitlines() if l.strip()][:8]
        step("检查本地改动", False,
             "检测到本地有未提交的改动，自动更新可能覆盖它们：\n" + "\n".join(changed))
        return {"ok": False, "steps": steps,
                "message": "本地有未提交的改动，已中止更新以免覆盖你的修改。"
                            "请先自行提交或用 git stash 暂存后再更新。"}
    step("检查本地改动", True, "工作区干净，可以安全更新")

    before = current_version()
    ok, out = _run_git(["pull", "--ff-only"], timeout=120)
    if not ok:
        step("拉取更新", False, out[:500])
        return {"ok": False, "steps": steps,
                "message": "git pull 失败。如果提示分支分叉，说明本地有和远端冲突的提交，"
                            "需要手动处理。"}
    step("拉取更新", True, out[:300] or "已是最新")

    after = current_version()
    if after != before:
        step("版本变更", True, f"{before} → {after}")
    else:
        step("版本变更", True, f"版本号未变（仍是 {after}），可能只是文档或非版本化改动")

    return {"ok": True, "steps": steps, "old_version": before, "new_version": after,
            "message": f"更新完成（{before} → {after}）。"
                        "依赖可能有变化，请**关闭程序并重新双击启动脚本**，"
                        "启动脚本会自动补装新增依赖。"}
