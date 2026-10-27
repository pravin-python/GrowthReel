"""The Django-login -> FastAPI bridge, plus this service's own session
lifecycle (access/refresh tokens, logout).

See backend/README.md "Contract for the FastAPI service" for the full
end-to-end flow this implements the FastAPI side of.
"""
from __future__ import annotations

from datetime import datetime, timezone

from asgiref.sync import sync_to_async
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.api.v1.deps import get_current_user
from app.api.v1.schemas import BridgeExchangeRequest, TokenResponse, UserOut
from app.core.config import settings
from app.core.redis_client import consume_bridge_jti, is_refresh_jti_revoked, revoke_refresh_jti
from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_bridge_token,
)

router = APIRouter()

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"

_UNAUTHORIZED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_TTL_SECONDS,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        samesite="lax",
        # Not secure in local http dev — a Secure cookie is silently dropped
        # by the browser over plain http://localhost, which would make login
        # impossible locally. Secure is enforced whenever ENV=="production".
        secure=settings.is_production,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post("/auth/exchange", response_model=TokenResponse)
async def exchange(body: BridgeExchangeRequest, response: Response) -> TokenResponse:
    from apps.users.models import User

    try:
        claims = verify_bridge_token(body.bridge_token)
    except InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc

    jti = claims.get("jti", "")
    if not await consume_bridge_jti(jti):
        raise _UNAUTHORIZED

    try:
        user = await sync_to_async(User.objects.get)(pk=claims["sub"])
    except (User.DoesNotExist, ValueError, TypeError, KeyError) as exc:
        raise _UNAUTHORIZED from exc

    if not user.is_active:
        raise _UNAUTHORIZED

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    _set_refresh_cookie(response, refresh_token)

    return TokenResponse(access_token=access_token, expires_in=settings.ACCESS_TOKEN_TTL_SECONDS)


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(request: Request, response: Response) -> TokenResponse:
    from apps.users.models import User

    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise _UNAUTHORIZED

    try:
        claims = decode_token(raw_refresh, expected_typ="refresh")
    except InvalidTokenError as exc:
        raise _UNAUTHORIZED from exc

    jti = claims.get("jti", "")
    if jti and await is_refresh_jti_revoked(jti):
        raise _UNAUTHORIZED

    try:
        user = await sync_to_async(User.objects.get)(pk=claims["sub"])
    except (User.DoesNotExist, ValueError, TypeError, KeyError) as exc:
        raise _UNAUTHORIZED from exc

    if not user.is_active:
        raise _UNAUTHORIZED

    # Rotate the refresh token on every use: revoke the old jti (best-effort)
    # and issue + set a brand new one. This bounds how long a stolen refresh
    # token stays useful to roughly one refresh cycle, at the cost of one
    # extra Redis write per refresh in production (documented tradeoff vs.
    # "just mint a new access token and leave the refresh cookie alone").
    if jti:
        exp = claims.get("exp")
        ttl = int(exp - datetime.now(tz=timezone.utc).timestamp()) if exp else 0
        await revoke_refresh_jti(jti, ttl)

    new_refresh_token = create_refresh_token(user)
    _set_refresh_cookie(response, new_refresh_token)

    access_token = create_access_token(user)
    return TokenResponse(access_token=access_token, expires_in=settings.ACCESS_TOKEN_TTL_SECONDS)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> Response:
    raw_refresh = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw_refresh:
        try:
            claims = decode_token(raw_refresh, expected_typ="refresh")
        except InvalidTokenError:
            claims = None
        if claims:
            jti = claims.get("jti", "")
            exp = claims.get("exp")
            if jti and exp:
                ttl = int(exp - datetime.now(tz=timezone.utc).timestamp())
                await revoke_refresh_jti(jti, ttl)

    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/auth/me", response_model=UserOut)
async def me(user=Depends(get_current_user)) -> UserOut:
    return UserOut(
        id=str(user.pk),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
    )
