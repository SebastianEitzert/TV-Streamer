"""LG webOS developer mode session: renew and check the remaining time.

Without a renewal, LG ends the developer mode after about 1000 hours and all
sideloaded apps (Moonlight) disappear. The session token comes from the webOS
Dev Manager / Developer Mode app; it is never logged.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import LG_CHECK_URL, LG_RENEW_URL

_TIME = re.compile(r"(\d+):(\d{1,2}):(\d{1,2})")
_TIMEOUT = ClientTimeout(total=20)


class LgError(Exception):
    """Renewal or check failed. The message never contains the token."""


@dataclass
class LgResult:
    """Answer of developer.lge.com."""

    ok: bool
    message: str
    remaining: timedelta | None = None


def token_from_input(value: str) -> str:
    """Accept the bare token or the full renewal URL and return the token."""
    value = (value or "").strip()
    if value.startswith(("http://", "https://")):
        tokens = parse_qs(urlparse(value).query).get("sessionToken")
        return tokens[0].strip() if tokens else ""
    return value


async def _call(session: ClientSession, url: str, token: str) -> LgResult:
    try:
        async with session.get(url, params={"sessionToken": token}, timeout=_TIMEOUT) as resp:
            text = await resp.text()
            status = resp.status
    except (ClientError, TimeoutError) as err:
        raise LgError(f"developer.lge.com not reachable: {type(err).__name__}") from None
    try:
        data = json.loads(text)
    except ValueError:
        data = {}
    message = str(data.get("errorMsg") or text[:200]).replace(token, "***")
    ok = status == 200 and str(data.get("result", "")).lower() == "success"
    remaining = None
    if ok and (m := _TIME.search(message)):
        remaining = timedelta(hours=int(m[1]), minutes=int(m[2]), seconds=int(m[3]))
    return LgResult(ok, message, remaining)


async def async_renew(session: ClientSession, token: str) -> LgResult:
    """Extend the developer mode session (same as the button in the Developer Mode app)."""
    return await _call(session, LG_RENEW_URL, token)


async def async_check(session: ClientSession, token: str) -> LgResult:
    """Ask how long the session is still valid."""
    return await _call(session, LG_CHECK_URL, token)
