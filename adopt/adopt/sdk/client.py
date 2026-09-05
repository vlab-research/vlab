"""The HTTP client for the vlab study-configuration service.

Wraps exactly the API `documentation/agent-api.md` describes, and nothing else:
study creation, the nine conf writes and the two reads, whole-study validation,
the optimize plan/apply pair, the read-only Meta proxy, and API-key listing and
revocation. Every method returns the parsed `data` payload and raises on a
non-2xx.

WHY THE ERRORS ARE TYPED
------------------------

The service answers a caller's mistakes with five distinguishable statuses and
three different `detail` SHAPES, and the difference matters for what a program
should do next:

* `400` — your request was malformed in a way the handler names: a blank or
  over-long study name, an ad-account id with the `act_` prefix, no Facebook
  credential at all. Deliberately NOT given its own type: every one of them is
  "read `detail` and fix the argument", which is what the base class already
  says, and a type nothing branches on is a name to maintain for nothing.
* `401` — the token is not usable at all. It never says why: signature, wrong
  audience, expired, revoked and tombstoned all collapse to
  `"Could not validate credentials"` (`server/deps.py`). Retrying is pointless.
* `403` — always a scope problem on this service, and the body names the scope
  or the path that was wanted. Also pointless to retry, but the fix is a
  different key rather than a different credential.
* `404` — the study, org or ad is not yours or does not exist. The two are
  deliberately indistinguishable.
* `409` — a name collision (study creation, API-key minting) or, on the Meta
  proxy, more than one Facebook credential with no `?credentials_key=` to pick
  between them. Recoverable, and the body says how.
* `422` — the body did not parse. FastAPI's `detail` is a LIST of per-field
  errors here, which is the most actionable failure the API has, and flattening
  it into `str(detail)` would throw away the `loc` that says which field.
* `5xx` — including the `500` that a POST to a nonexistent study produces
  (`study_confs.study_id` is `NOT NULL` and the insert's subselect yields
  `NULL`; §2.1), and the `500` the optimize routes turn every configuration
  failure into.

`detail`'s three shapes: a plain string on most routes, the `422` list, and an
OBJECT on the Meta proxy (`{message, meta_error: {code, subcode, type, ...}}`,
§2.5). `describe()` renders all three; `.detail` keeps the raw value so a
caller can branch on `meta_error["code"]`.

NO RETRIES, ANYWHERE
--------------------

Not on writes, because `study_confs` is append-only (§1.1): a POST that timed
out may well have inserted a row, and retrying it writes a second one. There is
no idempotency key and no way to withdraw the duplicate.

Not on reads either, though that is a weaker argument -- it is so that "the SDK
does not retry" is a single sentence a user can hold, rather than a rule with
an exception. `GET /{org}/optimize/{slug}` is the case that makes the
simplicity worth it: it looks like a read, it is documented as a preview, and
it writes three report rows and heals ad attributions every time it runs
(§11.3 of the plan). A retry policy keyed on the HTTP method would have
retried it.

`502` from the Meta proxy is the one place the API explicitly says "retry"
(§2.5). That is the caller's decision to make, with its own backoff; the
exception carries the status so it can.

INJECTABLE SESSION
------------------

`session` is anything with a `requests`-compatible
`request(method, url, *, params, json, headers, timeout)` returning an object
with `status_code`, `headers`, `text` and `json()`. `requests.Session` and
Starlette's `TestClient` both are, which is what lets the test suite drive the
real FastAPI app in-process instead of mocking the wire -- so a route that
changes shape breaks these tests rather than passing them.
"""

from __future__ import annotations

import json as _json
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import quote

# The production conf service. `devops/values/toixo-prod.yaml`, and the same
# host the dashboard's REACT_APP_CONF_SERVER_URL points at. NOT the Go service
# (`vlab-dashboard-api...`), which is Auth0-only and whose conf routes are dead
# (`documentation/agent-api.md`, "Two services, two base URLs").
DEFAULT_API_URL = "https://vlab-study-conf-api.toixo.vlab.digital"

# Generous. The optimize plan endpoint has a five-minute server-side budget of
# its own (`server.py`, `@async_timeout(300)`) and the Meta proxy 220 seconds,
# so a client timeout below those would abandon a request the server is still
# happily working on -- and for a write, abandoning it does not undo it.
DEFAULT_TIMEOUT_SECONDS = 310.0


class VlabError(Exception):
    """Base for everything this module raises.

    An `Exception`, never a `BaseException`. `study_conf.InvalidConfigError`
    was the latter and that is precisely why its careful messages reached a log
    instead of a caller for as long as they did (plan §11.4 item 1).
    """


class TransportError(VlabError):
    """The request never got an HTTP response: DNS, connection, socket timeout.

    Distinct from `ServerError` on purpose. A `502` means vlab answered and
    said Meta is unhappy; this means nothing answered, and the thing to check
    is the URL and the network rather than the request.
    """


class VlabHTTPError(VlabError):
    """A non-2xx response, with the pieces of it worth branching on."""

    def __init__(
        self,
        status_code: int,
        detail: Any,
        method: str,
        url: str,
        body_text: str = "",
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.method = method
        self.url = url
        self.body_text = body_text
        super().__init__(self.describe())

    # -- rendering ---------------------------------------------------------

    def describe(self) -> str:
        """A legible one-or-more-line rendering of whichever `detail` shape came back."""
        head = f"{self.status_code} from {self.method} {self.url}"
        lines = self.detail_lines()
        if not lines:
            return head
        if len(lines) == 1:
            return f"{head}: {lines[0]}"
        return "\n".join([head + ":"] + [f"  - {line}" for line in lines])

    def detail_lines(self) -> List[str]:
        """`detail`, as human-readable lines. One per field error for a 422."""
        detail = self.detail

        if detail is None:
            # No JSON body at all, or no `detail` key in it. An ingress or
            # proxy error page lands here; show enough of it to recognise.
            text = (self.body_text or "").strip()
            return [text[:500]] if text else []

        if isinstance(detail, str):
            return [detail]

        if isinstance(detail, list):
            if _looks_like_field_errors(detail):
                return [_field_error_line(item) for item in detail]
            # Some other JSON array. Rendering it as if it were FastAPI's
            # per-field errors would print `: ` for every element and claim a
            # structure it does not have.
            return [_compact(detail)]

        if isinstance(detail, dict):
            # The Meta proxy shape: {message, meta_error: {...}} (§2.5). Keep
            # the human sentence first and append the machine codes, because
            # Meta's `code`/`subcode` are what a caller looks up.
            message = detail.get("message")
            meta = detail.get("meta_error")
            line = str(message) if message is not None else _compact(detail)
            if isinstance(meta, dict):
                bits = [
                    f"{k}={meta[k]}"
                    for k in ("code", "subcode", "type", "http_status")
                    if meta.get(k) is not None
                ]
                if bits:
                    line = f"{line} [{', '.join(bits)}]"
            return [line]

        return [_compact(detail)]

    # -- the 422 half ------------------------------------------------------

    @property
    def field_errors(self) -> List[Dict[str, Any]]:
        """FastAPI's per-field errors, `[]` for any other `detail` shape.

        Each is `{"loc": [...], "msg": ..., "type": ...}`. `loc` starts with
        `"body"`, so `loc[1:]` is the path inside the conf you sent.

        Shape-checked, not merely type-checked. `detail` is whatever came back,
        and the fallback in `_error` puts a whole JSON body here when it has no
        `detail` key -- which an ingress or a proxy in front of the service can
        produce. Handing a caller a list of arbitrary dicts under a name that
        promises `loc` and `msg` turns their `fe["loc"]` into a `KeyError` on
        exactly the request that was already failing.
        """
        if _looks_like_field_errors(self.detail):
            return [item for item in self.detail if isinstance(item, dict)]
        return []


class NotAuthenticatedError(VlabHTTPError):
    """401. The token is not usable, and the service will not say why."""


class ForbiddenError(VlabHTTPError):
    """403. On this service, always a scope problem; the body names the scope."""


class NotFoundError(VlabHTTPError):
    """404. Not yours, or not there -- deliberately the same answer."""


class ConflictError(VlabHTTPError):
    """409. A taken name, or an ambiguous Facebook credential on the Meta proxy."""


class UnprocessableError(VlabHTTPError):
    """422. The body did not parse; see `field_errors`."""


class ServerError(VlabHTTPError):
    """5xx.

    Worth knowing which ones are routine rather than exceptional:

    * `500` on a conf POST to a study that does not exist (§2.1) -- confirm the
      slug rather than reading it as transient;
    * `500` from the optimize routes, which is where a run-time configuration
      failure is actually reported to a caller, with the message in `detail`;
    * `502` from the Meta proxy for a Meta 429/5xx or an unreachable Graph API.
      This one really is worth retrying, with the caller's own backoff.
    """


_STATUS_ERRORS = {
    401: NotAuthenticatedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableError,
}


def _looks_like_field_errors(value: Any) -> bool:
    """Is this FastAPI's `detail` for a 422, rather than some other array?

    Every entry has to carry `msg` -- pydantic emits it on every error and
    nothing else the service returns is a list of dicts with that key. An empty
    list is not field errors either: there would be nothing to report.
    """
    return (
        isinstance(value, list)
        and len(value) > 0
        and all(isinstance(item, dict) and "msg" in item for item in value)
    )


def _field_error_line(item: Any) -> str:
    if not isinstance(item, dict):
        return _compact(item)
    loc = item.get("loc") or []
    # Drop the leading "body"/"query" segment: the caller knows where it put
    # the value, and `body -> 0 -> name` reads worse than `[0].name`.
    if loc and loc[0] in ("body", "query", "path", "header"):
        loc = loc[1:]
    path = _render_loc(loc)
    msg = item.get("msg", "")
    return f"{path}: {msg}" if path else str(msg)


def _render_loc(loc: Sequence[Any]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        elif out:
            out += f".{part}"
        else:
            out = str(part)
    return out


def _compact(value: Any) -> str:
    try:
        return _json.dumps(value, default=str)
    except (TypeError, ValueError):
        return str(value)


class VlabClient:
    """A thin, typed client over the study-configuration API.

    :param api_key: the bearer token. Sent on every request.
    :param base_url: defaults to production; trailing slashes are trimmed.
    :param session: a `requests`-compatible session. Defaults to a fresh
        `requests.Session`, imported lazily so that importing this module
        costs nothing in an environment that only wants the pure halves.
    :param timeout: seconds, per request. See `DEFAULT_TIMEOUT_SECONDS`.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_API_URL,
        session: Any = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if session is None:
            import requests  # noqa: PLC0415 -- lazy on purpose, see docstring

            session = requests.Session()
        self.session = session

    # -- plumbing ----------------------------------------------------------

    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json: Any = None,
    ) -> Any:
        """One request. Returns the decoded body, or `None` for a 204.

        `params` entries whose value is `None` are dropped, so a caller can
        pass optional query parameters positionally without building the dict
        conditionally at every call site.
        """
        url = f"{self.base_url}{path}"
        query = {k: v for k, v in params.items() if v is not None} if params else None

        try:
            response = self.session.request(
                method,
                url,
                params=query,
                json=json,
                headers=self._headers(),
                timeout=self.timeout,
            )
        except VlabError:
            raise
        except Exception as e:  # noqa: BLE001 -- every transport failure, one type
            raise TransportError(f"{method} {url} failed: {e}") from e

        if response.status_code >= 400:
            raise self._error(method, url, response)

        if response.status_code == 204 or not (response.text or "").strip():
            return None

        try:
            return response.json()
        except ValueError as e:
            raise TransportError(
                f"{method} {url} returned {response.status_code} with a body that "
                f"is not JSON: {(response.text or '')[:200]!r}"
            ) from e

    def _error(self, method: str, url: str, response: Any) -> VlabHTTPError:
        text = response.text or ""
        detail: Any = None
        try:
            body = response.json()
            if isinstance(body, dict) and "detail" in body:
                detail = body["detail"]
            elif body is not None:
                detail = body
        except ValueError:
            detail = None

        status = response.status_code
        cls = _STATUS_ERRORS.get(
            status, ServerError if status >= 500 else VlabHTTPError
        )
        return cls(status, detail, method, url, text)

    def _data(self, *args: Any, **kwargs: Any) -> Any:
        """`request`, unwrapping the `{"data": ...}` envelope the API uses.

        Not every route wraps -- `GET /health` does not -- so an unwrapped body
        is returned as-is rather than raising, which keeps this usable as the
        one call site for everything below.
        """
        body = self.request(*args, **kwargs)
        if isinstance(body, dict) and "data" in body:
            return body["data"]
        return body

    # -- studies -----------------------------------------------------------

    def create_study(self, org_id: str, name: str) -> Dict[str, Any]:
        """`POST /{org}/studies`. Returns `{id, name, slug, createdAt}`.

        The slug is derived server-side and is NOT a slugification you can
        predict cheaply (apostrophes are deleted rather than replaced, among
        other things -- `server/slugify.py`). Read it off the response.
        """
        return self._data("POST", f"/{_seg(org_id)}/studies", json={"name": name})

    def get_confs(self, org_id: str, slug: str) -> Dict[str, Any]:
        """`GET /{org}/studies/{slug}/confs` -- newest row per conf type.

        Returns `{}` for a study with no configuration at all. (`agent-api.md`
        §2.3 says this raises a 500 in that case; it does not -- the dict
        comprehension in `db.get_all_study_confs` over an empty result set is
        simply an empty dict, and its `except IndexError` is unreachable. A
        test pins the real behaviour.)
        """
        return self._data("GET", f"/{_seg(org_id)}/studies/{_seg(slug)}/confs")

    def post_conf(
        self, org_id: str, slug: str, url_segment: str, body: Any
    ) -> Dict[str, Any]:
        """`POST /{org}/studies/{slug}/confs/{segment}` -- a whole section.

        `url_segment` is the HYPHENATED URL name (`data-sources`), not the
        stored conf type (`data_sources`); `study.SECTION_URL_SEGMENTS` maps
        between them. Append-only: this inserts a new row and supersedes the
        previous one, it does not update anything.
        """
        return self._data(
            "POST",
            f"/{_seg(org_id)}/studies/{_seg(slug)}/confs/{url_segment}",
            json=body,
        )

    def copy_from(self, org_id: str, slug: str, source_slug: str) -> Dict[str, Any]:
        """`POST /{org}/studies/{slug}/copy-from` -- every section but `general`."""
        return self._data(
            "POST",
            f"/{_seg(org_id)}/studies/{_seg(slug)}/copy-from",
            json={"source_study_slug": source_slug},
        )

    def validate(
        self, org_id: str, slug: str, sections: Optional[Mapping[str, Any]] = None
    ) -> Dict[str, Any]:
        """`POST /{org}/studies/{slug}/validate`. Returns the whole envelope.

        The envelope, not just `data`, because `known_gaps` sits beside it and
        is worth showing: it is what the verdict did not cover.

        `sections` is keyed AS STORED (`data_sources`, not `data-sources`) and
        REPLACES sections whole -- never a deep merge, because a write replaces
        a section whole. A `None` value removes a section for the purposes of
        the check.

        200 whether or not the study is valid. Branch on `data.valid`.
        """
        body = {"sections": dict(sections)} if sections is not None else None
        return self.request(
            "POST", f"/{_seg(org_id)}/studies/{_seg(slug)}/validate", json=body
        )

    # -- plan / apply ------------------------------------------------------

    def plan(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        """`GET /{org}/optimize/{slug}` -- the instruction list.

        **Not side-effect free**, despite being a GET and being documented as a
        preview: it heals ad attributions (writing `ad_attributions` rows),
        reads Meta, and writes an `adopt_reports` row plus two time-series
        reports (plan §11.3). It creates no Meta objects and spends no money.
        """
        return self._data("GET", f"/{_seg(org_id)}/optimize/{_seg(slug)}")

    def apply(
        self, org_id: str, slug: str, instruction: Mapping[str, Any]
    ) -> Dict[str, Any]:
        """`POST /{org}/optimize/{slug}/instruction` -- exactly one.

        Post the instruction back exactly as `plan` returned it: `params` goes
        to the Meta SDK verbatim. Re-plan after every apply -- reconciliation
        is layered, and an ad set's ads are not planned until the ad set exists
        on Meta (§5).
        """
        return self._data(
            "POST",
            f"/{_seg(org_id)}/optimize/{_seg(slug)}/instruction",
            json=dict(instruction),
        )

    def study_errors(self, org_id: str, slug: str) -> List[Dict[str, Any]]:
        """`GET /{org}/optimize/{slug}/errors`.

        swoosh's extraction errors only -- adopt writes no events at all, so an
        empty list is not evidence that ad building is healthy (§2.3).
        """
        return self._data("GET", f"/{_seg(org_id)}/optimize/{_seg(slug)}/errors")

    # -- the Meta proxy ----------------------------------------------------

    def meta_credentials(self, org_id: str) -> List[Dict[str, Any]]:
        """`GET /{org}/meta/credentials` -- names and entities, never tokens."""
        return self._data("GET", f"/{_seg(org_id)}/meta/credentials")

    def meta_adaccounts(
        self,
        org_id: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """`GET /{org}/meta/adaccounts`. Returns the envelope, for `paging`."""
        return self.request(
            "GET",
            f"/{_seg(org_id)}/meta/adaccounts",
            params={"credentials_key": credentials_key, "limit": limit, "after": after},
        )

    def meta_campaigns(
        self,
        org_id: str,
        account: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """`GET /{org}/meta/campaigns?account=`. `act_123` or `123` both work."""
        return self.request(
            "GET",
            f"/{_seg(org_id)}/meta/campaigns",
            params={
                "account": account,
                "credentials_key": credentials_key,
                "limit": limit,
                "after": after,
            },
        )

    def meta_adsets(
        self,
        org_id: str,
        campaign: str,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """`GET /{org}/meta/adsets?campaign=`.

        Each ad set goes straight into
        `adopt.authoring.extract.extract_from_adset` unchanged -- that is what
        `targeting` is in the field list for.
        """
        return self.request(
            "GET",
            f"/{_seg(org_id)}/meta/adsets",
            params={
                "campaign": campaign,
                "credentials_key": credentials_key,
                "limit": limit,
                "after": after,
            },
        )

    def meta_ads(
        self,
        org_id: str,
        campaign: Optional[str] = None,
        adset: Optional[str] = None,
        credentials_key: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> Dict[str, Any]:
        """`GET /{org}/meta/ads` -- exactly one of `campaign` or `adset`.

        The creative arrives nested under `creative`; store that blob verbatim
        as `creatives[].template`.
        """
        return self.request(
            "GET",
            f"/{_seg(org_id)}/meta/ads",
            params={
                "campaign": campaign,
                "adset": adset,
                "credentials_key": credentials_key,
                "limit": limit,
                "after": after,
            },
        )

    def meta_ad_creative(
        self, org_id: str, ad_id: str, credentials_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """`GET /{org}/meta/ads/{ad_id}/creative` -- the one blob."""
        return self._data(
            "GET",
            f"/{_seg(org_id)}/meta/ads/{_seg(ad_id)}/creative",
            params={"credentials_key": credentials_key},
        )

    # -- API keys ----------------------------------------------------------

    def list_api_keys(self) -> Dict[str, Any]:
        """`GET /users/api-keys`. Needs `auth:read`.

        Returns `{keys: [...], legacy_revocations: [...]}`. Keys minted before
        the 2026-09-04 hardening are not listed at all: nothing was ever stored
        for them, so there is nothing to list.
        """
        return self._data("GET", "/users/api-keys")

    def revoke_api_key(self, key_id: str) -> None:
        """`DELETE /users/api-keys/{id}`, where `id` is the `jti`. Needs `auth:write`.

        204 on success, 404 if the id is not one of *your* live keys -- never
        403, so it cannot be used to probe for someone else's key. The revoking
        replica drops it at once; others honour it for up to 30 seconds
        (`CACHE_TTL_SECONDS`). Treat revocation as "dead within a minute".
        """
        self.request("DELETE", f"/users/api-keys/{_seg(key_id)}")


def _seg(value: str) -> str:
    """Percent-encode one path segment.

    Slugs are `[a-z0-9-]` and org ids are UUIDs, so on well-formed input this
    is the identity. It exists for the ill-formed input: a slug with a `/` in
    it would otherwise silently address a different route, and a `?` would turn
    the rest of the path into a query string.
    """
    return quote(str(value), safe="")
