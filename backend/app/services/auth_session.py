"""
Session validation service.
Validates the current request's session cookie through the Better Auth service.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import current_app


class AuthServiceUnavailable(Exception):
    """Authentication service unavailable."""


def fetch_session(cookie_header: str | None):
    """Fetch the current session from the authentication service."""
    if not cookie_header:
        return None

    request = Request(
        current_app.config['AUTH_SESSION_ENDPOINT'],
        headers={
            'Accept': 'application/json',
            'Cookie': cookie_header
        },
        method='GET'
    )

    try:
        with urlopen(request, timeout=current_app.config['AUTH_SESSION_TIMEOUT']) as response:
            payload = json.loads(response.read().decode('utf-8'))
            if not payload or not payload.get('session') or not payload.get('user'):
                return None

            return payload
    except HTTPError as exc:
        if exc.code in (401, 403):
            return None
        raise AuthServiceUnavailable(f'Authentication service rejected the request: {exc.code}') from exc
    except URLError as exc:
        raise AuthServiceUnavailable('Authentication service is unavailable') from exc
