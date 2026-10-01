"""Payments, read-only: who the pay forms hold, what dinersclub refuses and
why, whether bails moved everyone they matched, and whether the providers can
keep paying. Paying and bailing belong in Fly's payment sub-bot. See README.md.
"""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional

import requests

from .. import io
from ..core import Finding, need, settings, utc

NAME = "payments"
# window_hours: how far back bail events and dinersclub lines are read.
# Refusals are grouped over it, so it must cover dean's re-drive interval.
DEFAULTS = {"held_minutes": 30, "responding_minutes": 10, "pattern_min_users": 3,
            "runway_hours_min": 6, "rate_hours": 24, "window_hours": 6, "bail_prefix": "",
            "ref_prefixes": [], "known_codes": [], "providers": ["dingconnect", "reloadly"],
            "dinersclub": {"namespace": "vprod", "deployment": "gbv-dinersclub"}}
BAIL_EVENTS, BAIL_LIMIT = "bails/events", 500
DING_API = "https://api.dingconnect.com/api/V1"
RELOADLY_API = "https://topups.reloadly.com"
DING_PAGE, DING_MAX_PAGES = 100, 50
WITHHOLD = re.compile(r"withholding (\S+) failure for user (\S+): code=(\S*) ")


def _states(survey_name: str, state: str) -> List[dict]:
    body = io.fly_get(f"surveys/{survey_name}/states", {"state": state, "limit": 10000})
    if int(body["total"]) != len(body["states"]):
        raise RuntimeError(f"{survey_name} {state}: got {len(body['states'])} of {body['total']} states")
    return body["states"]


def _bail_events(since: datetime) -> List[dict]:
    body = io.fly_get(BAIL_EVENTS, {"since": since.isoformat(), "limit": BAIL_LIMIT})
    # Fly sets `truncated` only when it cuts the page itself; on the user-wide
    # feed Exodus cuts at `limit` first, so a full page may hide more too.
    if body["truncated"] or len(body["items"]) >= BAIL_LIMIT:
        raise RuntimeError(f"Over {BAIL_LIMIT} bail events since {since}: some are unread")
    return body["items"]


def _dinersclub_lines(namespace: str, deployment: str, hours: float) -> List[str]:
    """dinersclub's `withholding` lines, each prefixed by kubelet's timestamp."""
    out = subprocess.run(["kubectl", "logs", "-n", namespace, f"deploy/{deployment}", "--timestamps",
                          f"--since={int(hours * 60)}m"], capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if "withholding" in line]


def _dingconnect(since: datetime) -> dict:
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
        if not body.get("ThereAreMoreItems") or (items and utc(items[-1]["StartedUtc"]) < since):
            break
    else:
        raise RuntimeError(f"DingConnect history since {since} is over {DING_MAX_PAGES} pages")
    return {"balance": balance["Balance"], "currency": balance["CurrencyIso"],
            "transfers": [t for t in transfers.values() if t["at"] and utc(t["at"]) >= since]}


def _reloadly(since: datetime) -> dict:
    """The wallet is shared with other studies, so all of them count toward the rate."""
    token = requests.post("https://auth.reloadly.com/oauth/token", timeout=io.TIMEOUT, json={
        "client_id": io.env("RELOADLY_ID"), "client_secret": io.env("RELOADLY_SECRET"),
        "grant_type": "client_credentials", "audience": RELOADLY_API})
    token.raise_for_status()
    headers = {"Authorization": "Bearer " + token.json()["access_token"],
               "Accept": "application/com.reloadly.topups-v1+json"}
    def get(path: str, params: Any = None) -> dict:
        r = requests.get(RELOADLY_API + path, headers=headers, params=params, timeout=io.TIMEOUT)
        r.raise_for_status()
        return r.json()
    balance = get("/accounts/balance")
    end = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    txns, page = [], 1
    while True:
        body = get("/topups/reports/transactions", {
            "size": 200, "page": page, "startDate": since.strftime("%Y-%m-%d %H:%M:%S"), "endDate": end})
        txns += [{"status": t.get("status"), "usd": t.get("requestedAmount") or 0,
                  "at": t.get("transactionDate")} for t in body["content"]]
        if body.get("last", True):
            break
        page += 1
    return {"balance": balance["balance"], "currency": balance["currencyCode"], "transfers": txns}


# provider -> (reader, status of a successful send)
PROVIDERS = {"dingconnect": (_dingconnect, "Complete"), "reloadly": (_reloadly, "SUCCESSFUL")}


def collect(cfg: Mapping[str, Any]) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    now = datetime.now(timezone.utc)
    countries = need(cfg, "countries").values()
    pay = {f for c in countries for f in c["pay"]}
    held, responding = [], []
    for c in countries:
        held += [{"userid": r["userid"], "form": r["current_form"], "form_start_time": r["form_start_time"]}
                 for r in _states(c["survey_name"], "WAIT_EXTERNAL_EVENT") if r["current_form"] in pay]
        responding += [{"userid": r["userid"], "form": r["current_form"], "updated": r["updated"]}
                       for r in _states(c["survey_name"], "RESPONDING")]
    bails = [e for e in _bail_events(now - timedelta(hours=s["window_hours"]))
             if (e.get("bail_name") or "").startswith(s["bail_prefix"])]
    d = {**DEFAULTS["dinersclub"], **s["dinersclub"]}
    since = now - timedelta(hours=s["rate_hours"])
    return {"held": held, "responding": responding, "bail_events": bails,
            "dinersclub": _dinersclub_lines(d["namespace"], d["deployment"], s["window_hours"]),
            "providers": {p: PROVIDERS[p][0](since) for p in s["providers"]}}


def stale(name: str, rows: List[dict], field: str, minutes: float, now: datetime, what: str,
          why: str) -> Finding:
    """`rows` whose `field` time is over `minutes` before `now`, oldest first."""
    rows = sorted((r for r in rows if utc(r[field]) < now - timedelta(minutes=minutes)),
                  key=lambda r: utc(r[field]))
    return Finding(NAME, "decision" if rows else "ok", f"{NAME}:{name}",
                   f"{len(rows)} {what} over {minutes} min"
                   + (f", oldest since {rows[0][field]}; {why}" if rows else ""), {name: rows})


def refusals(lines: Iterable[str], users: set, window_from: datetime, last: Optional[datetime],
             known: Iterable[str], min_users: int) -> List[Finding]:
    """One finding per (provider, code), by distinct `users` withheld in the
    window. Many numbers failing the same way is the form, the pin or the
    account; a few refused again and again is their line, which only a new
    number fixes. A line that does not parse is reported by the read that first
    sees it."""
    groups: Dict[tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unparsed = []
    for line in lines:
        stamp, _, rest = line.partition(" ")
        try:
            at = utc(stamp)
        except ValueError:
            at = None
        m = WITHHOLD.search(rest)
        if at and m:
            if at >= window_from and m.group(2) in users:
                groups[(m.group(1), m.group(3))][m.group(2)] += 1
        elif not at or at > (last or window_from):
            unparsed.append(line[:300])
    out = [Finding(NAME, "unknown", f"{NAME}:refusal:unparsed",
                   f"{len(unparsed)} dinersclub withholding line(s) did not parse",
                   {"lines": unparsed})] if unparsed else []
    for (provider, code), per_user in sorted(groups.items()):
        what = f"{provider} {code}: {len(per_user)} respondent(s) withheld since {window_from:%H:%M}Z"
        if code not in known:
            level, what = "unknown", f"Unknown error code. {what}"
        elif len(per_user) >= min_users:
            level, what = "decision", f"{what}: many numbers failing the same way, so the form, pin or account"
        else:
            level, what = "ok", f"{what}: the line(s); only a new number fixes it"
        out.append(Finding(NAME, level, f"{NAME}:refusal:{provider}:{code}", what,
                           {"provider": provider, "code": code, "per_user": dict(per_user)}))
    return out


def runway(provider: str, p: Mapping[str, Any], paid: str, hours: float, min_hours: float) -> Finding:
    """Hours the balance lasts at the last `hours`' rate of successful sends."""
    spent = sum(t["usd"] for t in p["transfers"] if t["status"] == paid)
    rate = spent / hours
    left = p["balance"] / rate if rate else float("inf")
    ev = {"balance": p["balance"], "currency": p["currency"], "spent": round(spent, 2),
          "rate_per_hour": round(rate, 2), "runway_hours": round(left, 1)}
    return Finding(NAME, "decision" if left < min_hours else "ok", f"{NAME}:runway:{provider}",
                   f"{provider} balance {p['balance']:.2f} {p['currency']}, "
                   f"{rate:.2f}/h over {hours}h: {left:.1f}h of runway", ev)


def double_completions(transfers: Iterable[dict], prefixes: Iterable[str], hours: float) -> Finding:
    """Study refs DingConnect completed more than once: it does not dedupe refs."""
    done: Dict[str, List[dict]] = defaultdict(list)
    for t in transfers:
        if t["status"] == PROVIDERS["dingconnect"][1] and t["ref"].startswith(tuple(prefixes)):
            done[t["ref"]].append(t)
    doubles = {ref: ts for ref, ts in done.items() if len(ts) > 1}
    extra = sum(t["usd"] for ts in doubles.values() for t in ts[1:])
    return Finding(NAME, "decision" if doubles else "ok", f"{NAME}:double-completion",
                   f"{len(doubles)} ref(s) completed more than once in {hours}h"
                   + (f", {extra:.2f} USD paid twice" if doubles else ""),
                   {"refs": doubles, "extra_usd": round(extra, 2)})


def check(cfg: Mapping[str, Any], snapshot: Mapping[str, Any], history: List[dict]) -> List[Finding]:
    s = settings(cfg, NAME, DEFAULTS)
    now = utc(snapshot["read_at"])
    last = utc(history[0]["read_at"]) if history else None
    window_from = now - timedelta(hours=s["window_hours"])
    out = [stale("held", snapshot["held"], "form_start_time", s["held_minutes"], now,
                 "held on a pay form", "the sweep should pay them"),
           stale("responding", snapshot["responding"], "updated", s["responding_minutes"], now,
                 "stuck in RESPONDING", "replybot drops their replies")]
    if last is None:
        out.append(Finding(NAME, "ok", f"{NAME}:gap", f"First read: bails and refusals over {s['window_hours']}h"))
    elif last < window_from:
        out.append(Finding(NAME, "unknown", f"{NAME}:gap", f"Bail events and dinersclub lines between "
                           f"{last.isoformat()} and {window_from.isoformat()} were not read"))

    events = [e for e in snapshot["bail_events"] if last is None or utc(e["timestamp"]) > last]
    bad = [e for e in events if e["users_matched"] != e["users_bailed"] or e["error"]]
    out += [Finding(NAME, "decision", f"{NAME}:bail:{e['bail_name']}",
                    f"Bail {e['bail_name']} matched {e['users_matched']}, bailed {e['users_bailed']}"
                    + (f", error {e['error']}" if e["error"] else ""), e) for e in bad]
    out += [] if bad else [Finding(NAME, "ok", f"{NAME}:bails",
                                   f"{len(events)} bail run(s) since the last read, each bailed all it matched")]
    out += refusals(snapshot["dinersclub"], {h["userid"] for h in snapshot["held"]}, window_from, last,
                    s["known_codes"], s["pattern_min_users"])
    out += [runway(name, p, PROVIDERS[name][1], s["rate_hours"], s["runway_hours_min"])
            for name, p in snapshot["providers"].items()]
    if "dingconnect" in snapshot["providers"]:
        out.append(double_completions(snapshot["providers"]["dingconnect"]["transfers"],
                                      s["ref_prefixes"], s["rate_hours"]))
    return out
