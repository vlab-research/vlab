"""Payments, read-only: who the pay forms are holding, what dinersclub is
refusing and why, whether the last bails moved everyone they matched, and
whether the providers can keep paying.

Paying and bailing are not here: they belong in Fly's payment sub-bot. A
finding says what a person (or the study's sweep) should do.

Sources. Fly's API for states and bail events. Until dinersclub, DingConnect
and Reloadly have Fly endpoints, each is read in one function below
(`_dinersclub_lines`, `_dingconnect`, `_reloadly`) so it can be swapped.

dinersclub's `withholding` line is the only one parsed: every withheld
failure logs one, with its code, including PIN_DRIFT, NO_PIN_FOR_OPERATOR and
codes dinersclub itself does not classify. The log is platform-wide, so only
lines for users the study's pay forms hold are kept.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

import requests

from .. import io
from ..core import Finding, need

NAME = "payments"
DEFAULTS = {
    "held_minutes": 30,
    "responding_minutes": 10,
    "pattern_min_users": 3,
    "runway_hours_min": 6,
    "rate_hours": 24,
    "bail_prefix": "",
    "ref_prefixes": [],
    "known_codes": [],
    "dinersclub": {"namespace": "vprod", "deployment": "gbv-dinersclub", "since": "65m"},
}
DING_API = "https://api.dingconnect.com/api/V1"
RELOADLY_API = "https://topups.reloadly.com"
DING_COMPLETE = "Complete"
DING_PAGE, DING_MAX_PAGES = 100, 50
WITHHOLD = re.compile(r"^(\S+) .*withholding (\S+) failure for user (\S+): code=(\S*) ")


def settings(cfg: Mapping[str, Any]) -> Dict[str, Any]:
    return {**DEFAULTS, **(cfg.get(NAME) or {})}


def _utc(s: str) -> datetime:
    """ISO 8601 with a Z, an offset, or naive (taken as UTC); nanoseconds cut."""
    s = re.sub(r"(\.\d{6})\d+", r"\1", s.replace("Z", "+00:00").replace(" ", "T", 1))
    t = datetime.fromisoformat(s)
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


# ---- collect ---------------------------------------------------------------

def _states(survey_name: str, state: str) -> List[dict]:
    body = io.fly_get(f"surveys/{survey_name}/states", {"state": state, "limit": 10000})
    if int(body["total"]) != len(body["states"]):
        raise RuntimeError(f"{survey_name} {state}: got {len(body['states'])} of {body['total']} states")
    return body["states"]


def _bail_events(limit: int = 100) -> List[dict]:
    """Fly's bail audit trail. REST serves it under /users/<vlab user id>/,
    which an API key cannot discover, so this goes through Fly's MCP tool over
    HTTP, which resolves the user from the key. The MCP transport answers 406
    unless the client accepts both JSON and an event stream."""
    url = os.environ.get("FLY_API_URL", io.FLY_API_URL).rstrip("/") + "/mcp"
    r = requests.post(url, timeout=io.TIMEOUT, headers={
        "Authorization": f"Bearer {io.env('FLY_API_KEY')}",
        "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "list_bail_events", "arguments": {"limit": limit}}})
    r.raise_for_status()
    body = r.json()
    result = body.get("result") or {}
    if "error" in body or result.get("isError"):
        raise RuntimeError(f"list_bail_events failed: {json.dumps(body)[:300]}")
    return json.loads(result["content"][0]["text"])["items"]


def _dinersclub_lines(d: Mapping[str, str]) -> List[str]:
    """dinersclub's `withholding` lines, each prefixed by kubelet's RFC 3339
    timestamp. Read with kubectl until dinersclub serves them."""
    out = subprocess.run(
        ["kubectl", "logs", "-n", d["namespace"], f"deploy/{d['deployment']}",
         f"--since={d['since']}", "--timestamps"],
        capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if "withholding" in line]


def _dingconnect(since: datetime) -> dict:
    """DingConnect balance and every transfer started since `since`, newest
    first as the API pages them."""
    headers = {"api_key": io.env("DINGCONNECT_API_KEY")}
    def call(method: str, path: str, **kw: Any) -> dict:
        r = requests.request(method, DING_API + path, headers=headers, timeout=io.TIMEOUT, **kw)
        r.raise_for_status()
        body = r.json()
        if body.get("ResultCode") != 1:
            raise RuntimeError(f"DingConnect {path}: {body.get('ErrorCodes')}")
        return body
    balance = call("GET", "/GetBalance")
    # Keyed by TransferRef: a transfer made while paging shifts the newest-first
    # list, so the same record can come back on two pages.
    transfers: Dict[str, dict] = {}
    for page in range(DING_MAX_PAGES):
        body = call("POST", "/ListTransferRecords", json={"Skip": page * DING_PAGE, "Take": DING_PAGE})
        items = [i.get("TransferRecord", i) for i in body.get("Items") or []]
        transfers.update({(t.get("TransferId") or {}).get("TransferRef"): {
            "ref": (t.get("TransferId") or {}).get("DistributorRef", ""),
            "status": t.get("ProcessingState"),
            "usd": (t.get("Price") or {}).get("SendValue") or 0,
            "at": t.get("StartedUtc")} for t in items})
        if not body.get("ThereAreMoreItems") or (items and _utc(items[-1]["StartedUtc"]) < since):
            break
    else:
        raise RuntimeError(f"DingConnect history since {since} is over {DING_MAX_PAGES} pages")
    return {"balance": balance["Balance"], "currency": balance["CurrencyIso"],
            "transfers": [t for t in transfers.values() if t["at"] and _utc(t["at"]) >= since]}


def _reloadly(since: datetime) -> dict:
    """Reloadly wallet balance and its transactions since `since`. The wallet
    is shared with other studies (Kenya), so all of them count toward the rate."""
    token = requests.post("https://auth.reloadly.com/oauth/token", timeout=io.TIMEOUT, json={
        "client_id": io.env("RELOADLY_ID"), "client_secret": io.env("RELOADLY_SECRET"),
        "grant_type": "client_credentials", "audience": RELOADLY_API})
    token.raise_for_status()
    headers = {"Authorization": "Bearer " + token.json()["access_token"],
               "Accept": "application/com.reloadly.topups-v1+json"}
    def get(path: str, params: Optional[dict] = None) -> dict:
        r = requests.get(RELOADLY_API + path, headers=headers, params=params, timeout=io.TIMEOUT)
        r.raise_for_status()
        return r.json()
    balance = get("/accounts/balance")
    txns, page = [], 1
    while True:
        body = get("/topups/reports/transactions", {
            "size": 200, "page": page, "startDate": since.strftime("%Y-%m-%d %H:%M:%S"),
            "endDate": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")})
        txns += [{"status": t.get("status"), "usd": t.get("requestedAmount") or 0,
                  "at": t.get("transactionDate")} for t in body["content"]]
        if body.get("last", True):
            break
        page += 1
    return {"balance": balance["balance"], "currency": balance["currencyCode"], "transfers": txns}


def collect(cfg: Mapping[str, Any]) -> dict:
    s = settings(cfg)
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=s["rate_hours"])
    countries = need(cfg, "countries")
    pay = {f for c in countries.values() for f in c["pay"]}
    held, responding = [], []
    for c in countries.values():
        held += [{"userid": r["userid"], "form": r["current_form"], "form_start_time": r["form_start_time"]}
                 for r in _states(c["survey_name"], "WAIT_EXTERNAL_EVENT") if r["current_form"] in pay]
        responding += [{"userid": r["userid"], "form": r["current_form"], "updated": r["updated"]}
                       for r in _states(c["survey_name"], "RESPONDING")]
    bails = [{k: e.get(k) for k in ("bail_name", "timestamp", "users_matched", "users_bailed", "error")}
             for e in _bail_events() if (e.get("bail_name") or "").startswith(s["bail_prefix"])]
    return {"at": now.isoformat(), "held": held, "responding": responding, "bail_events": bails,
            "dinersclub": _dinersclub_lines({**DEFAULTS["dinersclub"], **s["dinersclub"]}),
            "dingconnect": _dingconnect(since), "reloadly": _reloadly(since)}


# ---- check -----------------------------------------------------------------

def older_than(rows: Iterable[dict], field: str, now: datetime, minutes: float) -> List[dict]:
    """Rows whose `field` time is over `minutes` before `now`, oldest first."""
    cut = now - timedelta(minutes=minutes)
    return sorted((r for r in rows if _utc(r[field]) < cut), key=lambda r: _utc(r[field]))


def parse_withholding(lines: Iterable[str], since: Optional[datetime], users: set) -> List[dict]:
    """(at, provider, user, code) for each withholding line after `since` for
    one of `users`. A line that does not parse is kept with code None, so a
    changed log format reaches a person as an unknown code."""
    out = []
    for line in lines:
        m = WITHHOLD.match(line)
        if not m:
            out.append({"at": None, "provider": None, "user": None, "code": None, "line": line[:200]})
            continue
        at, provider, user, code = m.groups()
        if user in users and (since is None or _utc(at) > since):
            out.append({"at": at, "provider": provider, "user": user, "code": code})
    return out


def group_refusals(refusals: List[dict], known: Iterable[str], min_users: int) -> List[Finding]:
    """One finding per (provider, code). An unknown code is `unknown`. Many
    numbers failing the same way is the form, the pin or the account: a
    `decision`. A few numbers refused again and again is their line, which
    only a new number fixes: `ok`."""
    known = set(known)
    groups: Dict[tuple, Counter] = defaultdict(Counter)
    for r in refusals:
        groups[(r["provider"], r["code"])][r["user"]] += 1
    findings = []
    for (provider, code), users in sorted(groups.items(), key=str):
        ev = {"provider": provider, "code": code, "lines": sum(users.values()),
              "users": len(users), "per_user": dict(users)}
        key = f"{NAME}:refusal:{provider}:{code}"
        what = f"{provider} {code}: {ev['lines']} withheld sends to {len(users)} respondent(s)"
        if code not in known:
            findings.append(Finding(NAME, "unknown", key, f"Unknown error code. {what}", ev))
        elif len(users) >= min_users:
            findings.append(Finding(NAME, "decision", key,
                                    f"{what}: many numbers failing the same way, so the form, pin or account", ev))
        else:
            findings.append(Finding(NAME, "ok", key, f"{what}: the line(s); only a new number fixes it", ev))
    return findings


def runway(provider: str, p: Mapping[str, Any], paid: Iterable[str], hours: float,
           min_hours: float) -> Finding:
    """Hours the balance lasts at the last `hours`' rate of successful sends."""
    spent = sum(t["usd"] for t in p["transfers"] if t["status"] in paid)
    rate = spent / hours
    left = p["balance"] / rate if rate else float("inf")
    ev = {"balance": p["balance"], "currency": p["currency"], "spent": round(spent, 2),
          "rate_per_hour": round(rate, 2), "runway_hours": round(left, 1)}
    summary = (f"{provider} balance {p['balance']:.2f} {p['currency']}, "
               f"{rate:.2f}/h over {hours}h: {left:.1f}h of runway")
    level = "decision" if left < min_hours else "ok"
    return Finding(NAME, level, f"{NAME}:runway:{provider}", summary, ev)


def double_completions(transfers: Iterable[dict], prefixes: Iterable[str]) -> Dict[str, List[dict]]:
    """Study refs DingConnect completed more than once (it does not dedupe
    refs), each with its completed transfers."""
    prefixes = tuple(prefixes)
    done: Dict[str, List[dict]] = defaultdict(list)
    for t in transfers:
        if t["status"] == DING_COMPLETE and t["ref"].startswith(prefixes):
            done[t["ref"]].append(t)
    return {ref: ts for ref, ts in done.items() if len(ts) > 1}


def check(cfg: Mapping[str, Any], snapshot: Mapping[str, Any], history: List[dict]) -> List[Finding]:
    s = settings(cfg)
    now = _utc(snapshot["at"])
    last = _utc(history[0]["at"]) if history else None
    out: List[Finding] = []

    held = older_than(snapshot["held"], "form_start_time", now, s["held_minutes"])
    out.append(Finding(NAME, "decision" if held else "ok", f"{NAME}:held",
                       f"{len(held)} held on a pay form over {s['held_minutes']} min"
                       + (f", oldest since {held[0]['form_start_time']}; the sweep should pay them" if held else ""),
                       {"held": held}))

    stuck = older_than(snapshot["responding"], "updated", now, s["responding_minutes"])
    out.append(Finding(NAME, "decision" if stuck else "ok", f"{NAME}:responding",
                       f"{len(stuck)} stuck in RESPONDING over {s['responding_minutes']} min"
                       + (f", oldest since {stuck[0]['updated']}; replybot drops their replies" if stuck else ""),
                       {"stuck": stuck}))

    events = [e for e in snapshot["bail_events"] if last is None or _utc(e["timestamp"]) > last]
    bad = [e for e in events if e["users_matched"] != e["users_bailed"] or e["error"]]
    out += [Finding(NAME, "decision", f"{NAME}:bail:{e['bail_name']}",
                    f"Bail {e['bail_name']} matched {e['users_matched']}, bailed {e['users_bailed']}"
                    + (f", error {e['error']}" if e["error"] else ""), e) for e in bad]
    if not bad:
        out.append(Finding(NAME, "ok", f"{NAME}:bails",
                           f"{len(events)} bail run(s) since the last read, each bailed all it matched"))

    users = {h["userid"] for h in snapshot["held"]}
    out += group_refusals(parse_withholding(snapshot["dinersclub"], last, users),
                          s["known_codes"], s["pattern_min_users"])

    out.append(runway("dingconnect", snapshot["dingconnect"], [DING_COMPLETE], s["rate_hours"],
                      s["runway_hours_min"]))
    out.append(runway("reloadly", snapshot["reloadly"], ["SUCCESSFUL"], s["rate_hours"],
                      s["runway_hours_min"]))

    doubles = double_completions(snapshot["dingconnect"]["transfers"], s["ref_prefixes"])
    extra = sum(t["usd"] for ts in doubles.values() for t in ts[1:])
    out.append(Finding(NAME, "decision" if doubles else "ok", f"{NAME}:double-completion",
                       f"{len(doubles)} ref(s) completed more than once in {s['rate_hours']}h"
                       + (f", {extra:.2f} USD paid twice" if doubles else ""),
                       {"refs": doubles, "extra_usd": round(extra, 2)}))
    return out
