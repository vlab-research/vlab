import logging
import uuid
from datetime import datetime
from typing import Any, Dict

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


def generate_api_token(
    user_id: str,
    name: str,
) -> str:
    secret_key = API_KEY_SECRET
    now = datetime.utcnow()

    token_id = str(uuid.uuid4())

    payload = {
        "iss": API_KEY_DOMAIN,
        "aud": API_KEY_AUDIENCE,
        "iat": now,
        "jti": token_id,  # unique token ID
        "sub": str(user_id),
        "https://vlab.digital/token-name": name,
        "type": "api_key",  # custom claim to identify this as an API key
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token, token_id


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def verify_api_token(token: str) -> Dict[str, Any]:
    secret_key = API_KEY_SECRET

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            audience=API_KEY_AUDIENCE,
            issuer=API_KEY_DOMAIN,
        )

        # TODO: check payload ("id") against blacklist / whitelist

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
