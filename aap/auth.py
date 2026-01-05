import base64
import hashlib
import hmac
import os
import time
from typing import Optional

from . import config
from .utils import read_allowlist


def _get_totp_secret() -> Optional[bytes]:
    secret = os.environ.get(config.TOTP_SECRET_ENV)
    if not secret:
        return None
    try:
        return base64.b32decode(secret.upper())
    except Exception:
        return secret.encode()


def totp_now(interval: int = 30, digits: int = 6) -> str:
    secret = _get_totp_secret()
    if not secret:
        raise RuntimeError(f"TOTP secret missing; set {config.TOTP_SECRET_ENV}")
    timestep = int(time.time() // interval)
    msg = timestep.to_bytes(8, "big")
    h = hmac.new(secret, msg, hashlib.sha1).digest()
    o = h[-1] & 0x0F
    code = (int.from_bytes(h[o:o+4], "big") & 0x7FFFFFFF) % (10 ** digits)
    return str(code).zfill(digits)


def validate_totp(provided: str, interval: int = 30, window: int = 1, digits: int = 6) -> bool:
    secret = _get_totp_secret()
    if not secret:
        raise RuntimeError(f"TOTP secret missing; set {config.TOTP_SECRET_ENV}")
    try:
        val = int(provided)
    except ValueError:
        return False
    timestep = int(time.time() // interval)
    for offset in range(-window, window + 1):
        msg = (timestep + offset).to_bytes(8, "big")
        h = hmac.new(secret, msg, hashlib.sha1).digest()
        o = h[-1] & 0x0F
        code = (int.from_bytes(h[o:o+4], "big") & 0x7FFFFFFF) % (10 ** digits)
        if code == val:
            return True
    return False


def is_allowed_actor(actor: str) -> bool:
    allowlist = read_allowlist(config.AUTH_ALLOWLIST_FILE)
    return actor.lower() in allowlist if actor else False
