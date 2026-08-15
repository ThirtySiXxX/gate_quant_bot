"""
本地凭证存储：API Key/Secret 通过图形界面表单填写并保存到本地 json 文件，
不再需要手动编辑 .env。文件权限设置为仅当前用户可读写(600)。

注意：这只是"本地保存"，Secret 以明文存在这个 json 文件里（和大多数本地跑的
量化机器人做法一致），请勿把 data/ 目录上传到任何公开的代码仓库或分享给他人。
"""
from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Credentials:
    api_key: str = ""
    api_secret: str = ""
    api_host: str = "https://api.gateio.ws/api/v4"

    @property
    def is_set(self) -> bool:
        return bool(self.api_key) and bool(self.api_secret)

    def masked(self) -> dict:
        def mask(s: str) -> str:
            if not s:
                return ""
            if len(s) <= 8:
                return "*" * len(s)
            return s[:4] + "*" * (len(s) - 8) + s[-4:]
        return {
            "api_key": mask(self.api_key),
            "api_secret": mask(self.api_secret),
            "api_host": self.api_host,
            "is_set": self.is_set,
        }


class CredentialStore:
    def __init__(self, path: str = "./data/credentials.json"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    def load(self) -> Credentials:
        if not os.path.exists(self.path):
            return Credentials()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Credentials(
                api_key=data.get("api_key", "") or "",
                api_secret=data.get("api_secret", "") or "",
                api_host=data.get("api_host") or "https://api.gateio.ws/api/v4",
            )
        except Exception:
            return Credentials()

    def save(self, api_key: str, api_secret: str, api_host: Optional[str] = None) -> Credentials:
        creds = Credentials(
            api_key=api_key.strip(), api_secret=api_secret.strip(),
            api_host=(api_host or "https://api.gateio.ws/api/v4").strip(),
        )
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(asdict(creds), f, ensure_ascii=False, indent=2)
        try:
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
        return creds
