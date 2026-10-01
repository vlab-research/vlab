"""Shared IO for the checks. Credentials come from the environment."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable, Optional

import requests

from ..sdk.client import DEFAULT_API_URL, VlabClient

FLY_API_URL = "https://fly-dashboard-api.vlab.digital/api/v1"
TIMEOUT = 60


def env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def fly_get(path: str, params: Optional[dict] = None) -> Any:
    url = os.environ.get("FLY_API_URL", FLY_API_URL).rstrip("/") + "/" + path.lstrip("/")
    r = requests.get(url, params=params, timeout=TIMEOUT,
                     headers={"Authorization": f"Bearer {env('FLY_API_KEY')}"})
    r.raise_for_status()
    return r.json()


def vlab_client() -> VlabClient:
    return VlabClient(api_key=env("VLAB_API_KEY"),
                      base_url=os.environ.get("VLAB_API_URL", DEFAULT_API_URL))


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
