"""Payments, read-only: who the pay forms hold, what dinersclub refuses and
why, whether bails moved everyone they matched, and whether the providers can
keep paying. Paying and bailing belong in Fly's payment sub-bot. See README.md."""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .. import io
from ..core import Finding, need, settings, utc

M = Mapping[str, Any]
NAME = "payments"
DEFAULTS = {"held_minutes": 30, "responding_minutes": 10, "pattern_min_users": 3,
            "runway_hours_min": 6, "rate_hours": 24, "window_hours": 6, "bail_prefix": "",
            "ref_prefixes": [], "known_codes": [], "providers": ["dingconnect", "reloadly"],
            "dinersclub": {"namespace": "vprod", "deployment": "gbv-dinersclub"}}
BAIL_LIMIT = 500
DING_API = "https://api.dingconnect.com/api/V1"
RELOADLY_API = "https://topups.reloadly.com"
DING_PAGE, DING_MAX_PAGES = 100, 50
WITHHOLD = re.compile(r"withholding (\S+) failure for user (\S+): code=(\S*) ")


def _states(survey_name: str, state: str, field: str) -> List[dict]:
    body = io.fly_get("surveys", survey_name, "states", params={"state": state, "limit": 10000})
    if int(body["total"]) != len(body["states"]):
        raise RuntimeError(f"{survey_name} {state}: got {len(body['states'])} "
                           f"of {body['total']} states")
    return [{k: r[k] for k in ("userid", "current_form", field)} for r in body["states"]]


def _bail_events(since: datetime) -> List[dict]:
    body = io.fly_get("bails", "events", params={"since": since.isoformat(), "limit": BAIL_LIMIT})
    # Fly sets `truncated` only when it cuts the page itself; on the user-wide
    # feed Exodus cuts at `limit` first, so a full page may hide more too.
    if body["truncated"] or len(body["items"]) >= BAIL_LIMIT:
        raise RuntimeError(f"Over {BAIL_LIMIT} bail events since {since}: some are unread")
    return body["items"]


def _dinersclub_lines(namespace: str, deployment: str, hours: float) -> List[str]:
    """dinersclub's `withholding` lines, each prefixed by kubelet's timestamp."""
    run = subprocess.run(["kubectl", "logs", "-n", namespace, f"deploy/{deployment}",
                          "--timestamps", f"--since={int(hours * 60)}m"],
                         capture_output=True, text=True)
    if run.returncode:
        raise RuntimeError(f"kubectl logs {deployment}: {run.stderr.strip()[:300]}")
    return [line for line in run.stdout.splitlines() if "withholding" in line]


def _ding(method: str, path: str, **kw: Any) -> dict:
    body = io.http_json(method, DING_API + path,
                        headers={"api_key": io.env("DINGCONNECT_API_KEY")}, **kw)
    if body.get("ResultCode") != 1:
        raise RuntimeError(f"DingConnect {path}: {body.get('ErrorCodes')}")
    return body


def _dingconnect(since: datetime) -> dict:
    balance = _ding("GET", "/GetBalance")
    # Keyed by TransferRef: a transfer made while paging shifts the newest-first
    # list, so the same record can come back on two pages.
    transfers: Dict[str, dict] = {}
    for page in range(DING_MAX_PAGES):
        body = _ding("POST", "/ListTransferRecords",
                     json={"Skip": page * DING_PAGE, "Take": DING_PAGE})
        items = [i.get("TransferRecord", i) for i in body["Items"]]
        transfers.update({t["TransferId"]["TransferRef"]: {
            "ref": t["TransferId"].get("DistributorRef") or "", "status": t["ProcessingState"],
            "usd": t["Price"]["SendValue"], "at": t["StartedUtc"]} for t in items})
        if not body["ThereAreMoreItems"] or (items and utc(items[-1]["StartedUtc"]) < since):
            break
    else:
        raise RuntimeError(f"DingConnect history since {since} is over {DING_MAX_PAGES} pages")
    return {"balance": balance["Balance"], "currency": balance["CurrencyIso"],
            "transfers": [t for t in transfers.values() if utc(t["at"]) >= since]}


def _reloadly(since: datetime) -> dict:
    """The wallet is shared with other studies, so all of them count toward the rate."""
    token = io.http_json("POST", "https://auth.reloadly.com/oauth/token", json={
        "client_id": io.env("RELOADLY_ID"), "client_secret": io.env("RELOADLY_SECRET"),
        "grant_type": "client_credentials", "audience": RELOADLY_API})["access_token"]
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/com.reloadly.topups-v1+json"}
    balance = io.http_json("GET", RELOADLY_API + "/accounts/balance", headers=headers)
    fmt = "%Y-%m-%d %H:%M:%S"
    query = {"size": 200, "startDate": since.strftime(fmt),
             "endDate": (datetime.now(timezone.utc) + timedelta(days=1)).strftime(fmt)}
    txns: List[dict] = []
    for page in count(1):
        body = io.http_json("GET", RELOADLY_API + "/topups/reports/transactions",
                            headers=headers, params={**query, "page": page})
        txns += [{"status": t["status"], "usd": t["requestedAmount"], "at": t["transactionDate"]}
                 for t in body["content"]]
        if body["last"]:
            break
    return {"balance": balance["balance"], "currency": balance["currencyCode"], "transfers": txns}


# provider -> (reader, status of a successful send)
PROVIDERS = {"dingconnect": (_dingconnect, "Complete"), "reloadly": (_reloadly, "SUCCESSFUL")}


def collect(cfg: M) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    now = datetime.now(timezone.utc)
    waiting, responding = [], []
    for c in need(cfg, "countries").values():
        waiting += _states(c["survey_name"], "WAIT_EXTERNAL_EVENT", "form_start_time")
        responding += _states(c["survey_name"], "RESPONDING", "updated")
    d = s["dinersclub"]
    return {"waiting": waiting, "responding": responding,
            "bail_events": _bail_events(now - timedelta(hours=s["window_hours"])),
            "dinersclub": _dinersclub_lines(d["namespace"], d["deployment"], s["window_hours"]),
            "providers": {p: PROVIDERS[p][0](now - timedelta(hours=s["rate_hours"]))
                          for p in s["providers"]}}


def stale(name: str, rows: List[dict], field: str, minutes: float, now: datetime,
          what: str, why: str) -> Finding:
    """`rows` whose `field` time is over `minutes` before `now`, oldest first."""
    rows = sorted((r for r in rows if utc(r[field]) < now - timedelta(minutes=minutes)),
                  key=lambda r: utc(r[field]))
    tail = f", oldest since {rows[0][field]}; {why}" if rows else ""
    return Finding(NAME, "decision" if rows else "ok", f"{NAME}:{name}",
                   f"{len(rows)} {what} over {minutes} min{tail}", {name: rows})


def bails(events: Iterable[dict], prefix: str, last: Optional[datetime]) -> List[Finding]:
    """The study's bail runs since the last read that did not bail all they matched."""
    events = [e for e in events if (e["bail_name"] or "").startswith(prefix)
              and (last is None or utc(e["timestamp"]) > last)]
    bad = [Finding(NAME, "decision", f"{NAME}:bail:{e['bail_name']}",
                   f"Bail {e['bail_name']} matched {e['users_matched']}, bailed "
                   f"{e['users_bailed']}" + (f", error {e['error']}" if e["error"] else ""), e)
           for e in events if e["users_matched"] != e["users_bailed"] or e["error"]]
    return bad or [Finding(NAME, "ok", f"{NAME}:bails", f"{len(events)} bail run(s) since "
                           "the last read, each bailed all it matched")]


def refusals(lines: Iterable[str], users: set, window_from: datetime, last: Optional[datetime],
             known: Iterable[str], min_users: int) -> List[Finding]:
    """One finding per (provider, code), by distinct `users` withheld in the
    window (see README.md). A line that does not parse is reported by the read
    that first sees it."""
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
        what = (f"{provider} {code}: {len(per_user)} respondent(s) withheld "
                f"since {window_from:%H:%M}Z")
        if code not in known:
            level, what = "unknown", f"Unknown error code. {what}"
        elif len(per_user) >= min_users:
            level, what = "decision", f"{what}: many failing alike, so the form, pin or account"
        else:
            level, what = "ok", f"{what}: the line(s); only a new number fixes it"
        out.append(Finding(NAME, level, f"{NAME}:refusal:{provider}:{code}", what,
                           {"provider": provider, "code": code, "per_user": dict(per_user)}))
    return out


def runway(provider: str, p: M, paid: str, hours: float, min_hours: float) -> Finding:
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


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s = settings(cfg, NAME, DEFAULTS)
    now = utc(snapshot["read_at"])
    last = utc(history[0]["read_at"]) if history else None
    window_from = now - timedelta(hours=s["window_hours"])
    pay = {f for c in need(cfg, "countries").values() for f in c["pay"]}
    held = [r for r in snapshot["waiting"] if r["current_form"] in pay]
    out = [stale("held", held, "form_start_time", s["held_minutes"], now,
                 "held on a pay form", "the sweep should pay them"),
           stale("responding", snapshot["responding"], "updated", s["responding_minutes"], now,
                 "stuck in RESPONDING", "replybot drops their replies")]
    if last and last < window_from:
        out.append(Finding(NAME, "unknown", f"{NAME}:gap", f"Bail events and dinersclub lines "
                           f"between {last:%d %b %H:%M} and {window_from:%d %b %H:%M} UTC "
                           "were not read"))
    out += bails(snapshot["bail_events"], s["bail_prefix"], last)
    out += refusals(snapshot["dinersclub"], {h["userid"] for h in held}, window_from, last,
                    s["known_codes"], s["pattern_min_users"])
    out += [runway(name, p, PROVIDERS[name][1], s["rate_hours"], s["runway_hours_min"])
            for name, p in snapshot["providers"].items()]
    if "dingconnect" in snapshot["providers"]:
        out.append(double_completions(snapshot["providers"]["dingconnect"]["transfers"],
                                      s["ref_prefixes"], s["rate_hours"]))
    return out
