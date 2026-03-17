import time
import uuid
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from django.conf import settings


class JwtError(Exception):
    pass


def _jwt_secret() -> str:
    return getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)


def _jwt_algorithm() -> str:
    return getattr(settings, "JWT_ALGORITHM", "HS512")


def encode_jwt(payload: dict[str, Any]) -> str:
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_jwt(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            _jwt_secret(),
            algorithms=[_jwt_algorithm()],
            issuer=getattr(settings, "JWT_ISSUER", "finance-ai.local"),
        )
    except ExpiredSignatureError as exc:
        raise JwtError("Token expired") from exc
    except InvalidTokenError as exc:
        raise JwtError("Invalid token") from exc


def create_access_token(subject: str, scope: str) -> str:
    now = int(time.time())
    ttl_minutes = getattr(settings, "JWT_ACCESS_TOKEN_LIFETIME_MINUTES", 30)
    payload = {
        "iss": getattr(settings, "JWT_ISSUER", "finance-ai.local"),
        "sub": subject,
        "exp": now + (ttl_minutes * 60),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "scope": scope,
    }
    return encode_jwt(payload)


def create_refresh_token(subject: str) -> str:
    now = int(time.time())
    ttl_days = getattr(settings, "JWT_REFRESH_TOKEN_LIFETIME_DAYS", 7)
    payload = {
        "iss": getattr(settings, "JWT_ISSUER", "finance-ai.local"),
        "sub": subject,
        "exp": now + (ttl_days * 24 * 60 * 60),
        "iat": now,
        "jti": str(uuid.uuid4()),
        "typ": "refresh",
    }
    return encode_jwt(payload)


def validate_refresh_token(token: str) -> dict[str, Any]:
    payload = decode_jwt(token)
    if payload.get("typ") != "refresh":
        raise JwtError("Invalid refresh token")
    return payload
