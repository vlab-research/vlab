"""Shared IO for the checks. Credentials come from the environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import quote

import requests

from ..sdk.client import DEFAULT_API_URL, VlabClient

FLY_API_URL = "https://fly-dashboard-api.vlab.digital/api/v1"
TIMEOUT = 60


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def http_json(method: str, url: str, **kw: Any) -> Any:
    r = requests.request(method, url, timeout=TIMEOUT, **kw)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} from {method} {r.url}: {r.text[:300]}")
    return r.json()


def _fly(method: str, path: Iterable[str], **kw: Any) -> Any:
    url = "/".join([os.environ.get("FLY_API_URL", FLY_API_URL).rstrip("/"),
                    *(quote(p, safe="") for p in path)])
    return http_json(method, url, headers={"Authorization": f"Bearer {env('FLY_API_KEY')}"}, **kw)


def fly_get(*path: str, params: Optional[dict] = None) -> Any:
    """GET Fly's `path` parts, each quoted (survey names hold spaces)."""
    return _fly("GET", path, params=params)


def fly_post(*path: str, body: Any = None) -> Any:
    return _fly("POST", path, json=body)


def vlab_client() -> VlabClient:
    return VlabClient(api_key=env("VLAB_API_KEY"),
                      base_url=os.environ.get("VLAB_API_URL", DEFAULT_API_URL))


def load_env_files(study_dir: Path, paths: Iterable[str]) -> None:
    """KEY=VALUE lines from each file into the environment, never overriding."""
    for rel in paths:
        for line in (Path(study_dir) / rel).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"'))
