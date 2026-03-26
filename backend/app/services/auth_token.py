"""
Privy Access Token 校验服务
"""

import jwt
from flask import current_app, request
from jwt import ExpiredSignatureError, InvalidTokenError


class InvalidAuthToken(Exception):
    """无效或过期的认证 Token"""


def extract_access_token():
    """从 Authorization Header 或 privy-token Cookie 提取 Access Token"""
    auth_header = request.headers.get('Authorization', '')

    if auth_header.startswith('Bearer '):
        return auth_header.replace('Bearer ', '', 1).strip()

    cookie_token = request.cookies.get('privy-token')
    if cookie_token:
        return cookie_token.strip()

    return None


def verify_access_token(access_token: str):
    """校验 Privy 签发的 Access Token"""
    if not access_token:
        return None

    try:
        return jwt.decode(
            access_token,
            current_app.config['PRIVY_VERIFICATION_KEY'],
            algorithms=['ES256'],
            audience=current_app.config['PRIVY_APP_ID'],
            issuer=current_app.config['PRIVY_TOKEN_ISSUER'],
            options={'require': ['sub', 'aud', 'iss', 'exp']}
        )
    except (ExpiredSignatureError, InvalidTokenError) as exc:
        raise InvalidAuthToken('Invalid Privy access token') from exc
