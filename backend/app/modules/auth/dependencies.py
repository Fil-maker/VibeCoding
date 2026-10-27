"""The auth context of a request: `current_user` and `current_admin`.

These are the entry point other modules' routers use to learn who is calling.
"""

from typing import Annotated

from fastapi import Cookie, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.errors import NotSignedIn
from app.modules.auth.service import resolve_session
from app.platform.auth_context import AuthContext, Role
from app.platform.clock import Clock, get_clock
from app.platform.db import get_database_session
from app.platform.errors import NotFound
from app.platform.settings import Settings

SESSION_COOKIE = "vc_session"
SECONDS_PER_DAY = 24 * 60 * 60


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    """Put the session token into the `vc_session` cookie of a response."""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_lifetime_days * SECONDS_PER_DAY,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


async def current_user(
    session: Annotated[AsyncSession, Depends(get_database_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthContext:
    """The caller; 401 `not_signed_in` without a live session of a confirmed, active user."""
    if session_token is None:
        raise NotSignedIn
    context = await resolve_session(session, session_token, clock.now())
    if context is None:
        raise NotSignedIn
    return context


async def current_admin(
    context: Annotated[AuthContext, Depends(current_user)],
) -> AuthContext:
    """The caller if an administrator; anyone else gets 404, as if the page were absent."""
    if context.role is not Role.ADMINISTRATOR:
        raise NotFound
    return context
