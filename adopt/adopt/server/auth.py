import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import requests
from environs import Env
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

env = Env()

AUTH0_DOMAIN = env("AUTH0_DOMAIN")
AUTH0_AUDIENCE = env("AUTH0_AUDIENCE")
ALGORITHMS = ["RS256"]
API_KEY_DOMAIN = env("API_KEY_DOMAIN")
API_KEY_AUDIENCE = env("API_KEY_AUDIENCE")
API_KEY_SECRET = env("API_KEY_SECRET")

# Namespaced claims, so nothing here can collide with a registered JWT claim or
# with Auth0's own `scope`/`permissions` on RS256 tokens.
NAME_CLAIM = "https://vlab.digital/token-name"
SCOPES_CLAIM = "https://vlab.digital/scopes"

# The compatibility switch, and the one place vlab could not copy fly.
#
# fly discriminates hardened keys from legacy ones by the presence of a `jti`.
# vlab cannot: `generate_api_token` has ALWAYS minted a jti — it just threw it
# away instead of persisting it (the `# TODO: check payload ("id") against
# blacklist / whitelist` below). So every key in production carries a jti with
# no row behind it, and requiring a row for any token with a jti would revoke
# every key in existence the moment this deploys.
#
# Hence an explicit version claim, written only by the hardened mint path:
#
#   version >= 2  -> a credentials row is REQUIRED (see api_keys.assert_token_row_live)
#   absent        -> legacy: accepted with no row, exactly as before
#
# A legacy token cannot forge its way into v2 or out of it: the claim is inside
# the signature. The cost of this choice is that existing keys stay eternal
# until reissued, and are killable only by the coarse (user, name) tombstone in
# api_keys.legacy_key_revoked. That is a deliberate trade of "nobody's key
# breaks today" against "old keys stay weak until rotated".
VERSION_CLAIM = "https://vlab.digital/token-version"
TOKEN_VERSION = 2

# 90 days, matching fly. Long enough that a researcher's own key is not a chore;
# short enough that a key forgotten in a notebook dies on its own.
API_TOKEN_TTL_DAYS = 90
MAX_API_TOKEN_TTL_DAYS = 365


def generate_api_token(
    user_id: str,
    name: str,
    scopes: Optional[List[str]] = None,
    ttl_days: int = API_TOKEN_TTL_DAYS,
    issued_at: Optional[datetime] = None,
) -> Tuple[str, str]:
    """Mint a v2 API key AND persist its credentials row. Returns (token, jti).

    The two halves are ONE operation on purpose. Validity is positive — a key is
    live iff its row is live — so a token minted without its row is dead on
    arrival, and splitting minting from persisting makes that a footgun rather
    than a compile error. The existing inline `POST /users/api-key` in server.py
    calls this with two arguments and gets a working, revocable, expiring key
    without knowing any of the above; that is the point.

    `exp` is unconditional here. vlab can require it where fly could not:
    `API_KEY_SECRET` is read in exactly one place (this module) and nothing else
    in the repo signs with it, so there are no internal service JWTs sharing the
    secret that would break under a mandatory expiry.

    Raises psycopg.errors.UniqueViolation when the user already has a live key
    with this name (unique_entity_key_per_user).
    """
    now = issued_at or datetime.now(timezone.utc)
    expires_at = now + timedelta(days=ttl_days)
    token_id = str(uuid.uuid4())

    payload: Dict[str, Any] = {
        "iss": API_KEY_DOMAIN,
        "aud": API_KEY_AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": token_id,  # unique token ID; the key of the credentials row
        "sub": str(user_id),
        NAME_CLAIM: name,
        "type": "api_key",  # custom claim to identify this as an API key
        VERSION_CLAIM: TOKEN_VERSION,
    }

    # Absent, not null, when unrestricted — an absent scopes claim is what
    # "unrestricted" means throughout this scheme.
    if scopes:
        payload[SCOPES_CLAIM] = scopes

    # Lazy import: api_keys imports this module. See verify_api_token below.
    from .api_keys import persist_api_token

    # Before the token is returned, so a failed write never hands out a key.
    persist_api_token(
        user_id=str(user_id),
        name=name,
        jti=token_id,
        scopes=scopes,
        issued_at=now,
        expires_at=expires_at,
    )

    token = jwt.encode(payload, API_KEY_SECRET, algorithm="HS256")
    return token, token_id


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def verify_api_token(token: str) -> Dict[str, Any]:
    secret_key = API_KEY_SECRET

    try:
        # `exp` is verified when present and not required when absent, which is
        # precisely the legacy-compatibility behaviour we want: v2 tokens always
        # carry one (and api_keys.assert_token_row_live additionally REQUIRES
        # one of them), pre-hardening tokens never did.
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            audience=API_KEY_AUDIENCE,
            issuer=API_KEY_DOMAIN,
        )

        # This is what the old `# TODO: check payload ("id") against blacklist /
        # whitelist` was standing in for — except positive rather than a
        # blacklist: a v2 key is live iff its credentials row is live.
        #
        # Imported lazily because `api_keys` imports this module for AuthError
        # and generate_api_token, so a module-level import here is a cycle. It
        # is a real import rather than a registration hook on purpose: if
        # api_keys fails to import, this raises loudly instead of silently
        # disabling revocation.
        from .api_keys import assert_token_row_live

        assert_token_row_live(payload)

        return payload

    except ExpiredSignatureError:
        raise AuthError(
            {"code": "token_expired", "description": "Token has expired"}, 401
        )
    except JWTClaimsError:
        raise AuthError(
            {
                "code": "invalid_claims",
                "description": "Incorrect claims. Please check the audience and issuer.",
            },
            401,
        )
    except JWTError:
        raise AuthError(
            {
                "code": "invalid_token",
                "description": "There is an issue with the token you provied for authentication",
            },
            401,
        )


class DifferentAuthError(BaseException):
    pass


def verify_token(token: str) -> Dict[str, Any]:
    res = requests.get(AUTH0_DOMAIN + ".well-known/jwks.json")
    jwks = res.json()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        raise AuthError(
            {
                "code": "invalid_header",
                "description": "Unable to parse authentication" " token.",
            },
            401,
        )

    rsa_key = {}
    for key in jwks["keys"]:
        if "kid" not in unverified_header:
            raise DifferentAuthError("Not client token")

        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=AUTH0_AUDIENCE,
                    issuer=AUTH0_DOMAIN,
                )
            except ExpiredSignatureError:
                raise AuthError(
                    {"code": "token_expired", "description": "token is expired"}, 401
                )
            except JWTClaimsError:
                raise AuthError(
                    {
                        "code": "invalid_claims",
                        "description": "incorrect claims,"
                        "please check the audience and issuer",
                    },
                    401,
                )
            except Exception:
                raise AuthError(
                    {
                        "code": "invalid_header",
                        "description": "Unable to parse authentication" " token.",
                    },
                    401,
                )

            return payload
        raise AuthError(
            {"code": "invalid_header", "description": "Unable to find appropriate key"},
            401,
        )


def verify_tokens(token: str) -> Dict[str, Any]:
    try:
        return verify_token(token)

    except DifferentAuthError:
        try:
            return verify_api_token(token)

        except AuthError as second_error:
            logging.error(second_error)
            raise second_error

    except AuthError as error:
        raise error
