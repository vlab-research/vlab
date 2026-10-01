"""Shared IO for the checks. Credentials come from the environment."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional

import requests

from ..sdk.client import DEFAULT_API_URL, VlabClient

FLY_API_URL = "https://fly-dashboard-api.vlab.digital/api/v1"
CRDB_NS, CRDB_POD = "vprod", "gbv-cockroachdb-0"
TIMEOUT = 60


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def _fly(method: str, path: str, **kw: Any) -> Any:
    url = os.environ.get("FLY_API_URL", FLY_API_URL).rstrip("/") + "/" + path.lstrip("/")
    headers = {"Authorization": f"Bearer {env('FLY_API_KEY')}"}
    r = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def fly_get(path: str, params: Optional[dict] = None) -> Any:
    return _fly("GET", path, params=params)


def fly_post(path: str, body: Any) -> Any:
    return _fly("POST", path, json=body)


def vlab_client() -> VlabClient:
    return VlabClient(api_key=env("VLAB_API_KEY"),
                      base_url=os.environ.get("VLAB_API_URL", DEFAULT_API_URL))


def meta_token(key: str = "virtual-lab-vlab") -> str:
    """FACEBOOK_ACCESS_TOKEN, else the facebook_ad_user token in prod's
    credentials table, read through kubectl so it never appears in argv."""
    if os.environ.get("FACEBOOK_ACCESS_TOKEN"):
        return os.environ["FACEBOOK_ACCESS_TOKEN"]
    sql = ("SELECT details->>'access_token' FROM credentials "
           f"WHERE entity='facebook_ad_user' AND key='{key}'")
    out = subprocess.run(
        ["kubectl", "exec", "-n", CRDB_NS, CRDB_POD, "--", "./cockroach", "sql",
         "--insecure", "--database=chatroach", "--format=csv", "-e", sql],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()
    if len(out) < 2:
        raise RuntimeError(f"No facebook_ad_user credential with key={key!r} in prod")
    return out[-1].strip()


def load_env_files(study_dir: Path, paths: Iterable[str]) -> None:
    """Set KEY=VALUE lines from each file (relative to the study dir) into the
    environment, never overriding a variable already set."""
    for rel in paths:
        with open(Path(study_dir) / rel) as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))
