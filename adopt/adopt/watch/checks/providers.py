"""Payment providers, read-only: what dinersclub refuses and why, whether the
wallets can keep paying, and refs paid twice. Each is read only when configured
(`dinersclub`, `wallets`, `ref_prefixes`), locally in one function until Fly or
dinersclub serves it. See README.md."""

from __future__ import annotations

import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Dict, Iterable, List, Mapping, Optional

from .. import io
from ..core import Finding, need, settings, utc
from .payments import gap, held_on_pay_form, waiting_on_pay

M = Mapping[str, Any]
NAME = "providers"
DEFAULTS = {"pattern_min_users": 3, "runway_hours_min": 6, "rate_hours": 24, "window_hours": 6,
            "ref_prefixes": [], "known_codes": [], "wallets": [], "dinersclub": None}
DING_API = "https://api.dingconnect.com/api/V1"
RELOADLY_API = "https://topups.reloadly.com"
DING_PAGE, DING_MAX_PAGES = 100, 50
WITHHOLD = re.compile(r"withholding (?P<provider>\S+) failure for user (?P<user>\S+): "
                      r"code=(?P<code>\S*) ")
# A code dinersclub's classify.go has no recovery for, withheld as a precondition.
UNCLASSIFIED = re.compile(r"unclassified (?P<provider>\S+) error code \"(?P<code>[^\"]*)\" "
                          r"for user (?P<user>\S+) -- withholding")


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
    # list, so the same record can come back on two pages. A failed transfer
    # has no Price; any other without one raises.
    transfers: Dict[str, dict] = {}
    for page in range(DING_MAX_PAGES):
        body = _ding("POST", "/ListTransferRecords",
                     json={"Skip": page * DING_PAGE, "Take": DING_PAGE})
        items = [i.get("TransferRecord", i) for i in body["Items"]]
        transfers.update({t["TransferId"]["TransferRef"]: {
            "ref": t["TransferId"].get("DistributorRef") or "", "status": t["ProcessingState"],
            "amount": None if t["ProcessingState"] == "Failed" else t["Price"]["SendValue"],
            "at": t["StartedUtc"]} for t in items})
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
        txns += [{"status": t["status"], "amount": t["requestedAmount"], "at": t["transactionDate"]}
                 for t in body["content"]]
        if body["last"]:
            break
    return {"balance": balance["balance"], "currency": balance["currencyCode"], "transfers": txns}


# provider -> (reader, status of a successful send)
PROVIDERS = {"dingconnect": (_dingconnect, "Complete"), "reloadly": (_reloadly, "SUCCESSFUL")}


def collect(cfg: M) -> dict:
    s = settings(cfg, NAME, DEFAULTS)
    now = datetime.now(timezone.utc)
    lines = _dinersclub_lines(need(cfg, f"{NAME}.dinersclub.namespace"),
                              need(cfg, f"{NAME}.dinersclub.deployment"),
                              s["window_hours"]) if s["dinersclub"] else []
    return {"waiting": waiting_on_pay(cfg) if s["dinersclub"] else [], "dinersclub": lines,
            "providers": {p: PROVIDERS[p][0](now - timedelta(hours=s["rate_hours"]))
                          for p in s["wallets"]}}


def refusals(lines: Iterable[str], users: set, window_from: datetime, last: Optional[datetime],
             known: Iterable[str], min_users: int) -> List[Finding]:
    """One finding per (provider, code), by distinct `users` withheld in the
    window (see README.md). A line that does not parse is reported by the read
    that first sees it."""
    groups: Dict[tuple, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unclassified, unparsed = set(), []
    for line in lines:
        stamp, _, rest = line.partition(" ")
        try:
            at = utc(stamp)
        except ValueError:
            at = None
        m = WITHHOLD.search(rest) or UNCLASSIFIED.search(rest)
        if at and m:
            key = (m["provider"], m["code"])
            if at >= window_from and m["user"] in users:
                groups[key][m["user"]] += 1
            if m.re is UNCLASSIFIED:
                unclassified.add(key)
        elif not at or at > (last or window_from):
            unparsed.append(line[:300])
    out = [Finding(NAME, "unknown", f"{NAME}:refusal:unparsed",
                   f"{len(unparsed)} dinersclub withholding line(s) did not parse",
                   {"lines": unparsed})] if unparsed else []
    for (provider, code), per_user in sorted(groups.items()):
        what = (f"{provider} {code}: {len(per_user)} respondent(s) withheld "
                f"since {window_from:%H:%M}Z")
        if code not in known:
            level = "unknown"
            what = ("Error code unclassified by dinersclub. " if (provider, code) in unclassified
                    else "Unknown error code. ") + what
        elif len(per_user) >= min_users:
            level, what = "decision", f"{what}: many failing alike, so the form, pin or account"
        else:
            level, what = "ok", f"{what}: the line(s); only a new number fixes it"
        out.append(Finding(NAME, level, f"{NAME}:refusal:{provider}:{code}", what,
                           {"provider": provider, "code": code, "per_user": dict(per_user)}))
    return out


def runway(provider: str, p: M, paid: str, hours: float, min_hours: float) -> Finding:
    """Hours the balance lasts at the last `hours`' rate of successful sends."""
    spent = sum(t["amount"] for t in p["transfers"] if t["status"] == paid)
    rate = spent / hours
    left = p["balance"] / rate if rate else float("inf")
    ev = {"balance": p["balance"], "currency": p["currency"], "spent": round(spent, 2),
          "rate_per_hour": round(rate, 2), "runway_hours": round(left, 1)}
    pace = f"{rate:.2f}/h over {hours}h: {left:.1f}h of runway" if rate else f"no sends in {hours}h"
    return Finding(NAME, "decision" if left < min_hours else "ok", f"{NAME}:runway:{provider}",
                   f"{provider} balance {p['balance']:.2f} {p['currency']}, {pace}", ev)


def double_completions(p: M, prefixes: Iterable[str], hours: float) -> Finding:
    """Study refs DingConnect completed more than once: it does not dedupe refs."""
    done: Dict[str, List[dict]] = defaultdict(list)
    for t in p["transfers"]:
        if t["status"] == PROVIDERS["dingconnect"][1] and t["ref"].startswith(tuple(prefixes)):
            done[t["ref"]].append(t)
    doubles = {ref: ts for ref, ts in done.items() if len(ts) > 1}
    extra = sum(t["amount"] for ts in doubles.values() for t in ts[1:])
    return Finding(NAME, "decision" if doubles else "ok", f"{NAME}:double-completion",
                   f"{len(doubles)} ref(s) completed more than once in {hours}h"
                   + (f", {extra:.2f} {p['currency']} paid twice" if doubles else ""),
                   {"refs": doubles, "extra": round(extra, 2), "currency": p["currency"]})


def check(cfg: M, snapshot: M, history: List[dict]) -> List[Finding]:
    s = settings(cfg, NAME, DEFAULTS)
    now = utc(snapshot["read_at"])
    last = utc(history[0]["read_at"]) if history else None
    window_from = now - timedelta(hours=s["window_hours"])
    out = []
    if s["dinersclub"]:
        out += gap(NAME, "dinersclub lines", last, window_from)
        out += refusals(snapshot["dinersclub"],
                        {h["userid"] for h in held_on_pay_form(cfg, snapshot["waiting"])},
                        window_from, last, s["known_codes"], s["pattern_min_users"])
    out += [runway(name, p, PROVIDERS[name][1], s["rate_hours"], s["runway_hours_min"])
            for name, p in snapshot["providers"].items()]
    if s["ref_prefixes"] and "dingconnect" in snapshot["providers"]:
        out.append(double_completions(snapshot["providers"]["dingconnect"],
                                      s["ref_prefixes"], s["rate_hours"]))
    return out
