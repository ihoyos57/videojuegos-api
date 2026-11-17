"""A short-lived, HMAC-authenticated, audience-scoped per-request machine proof.

Not equivalent to GCP workload identity federation: both services share a secret.
Used only when SECURITY_AUTH_MODE=protected and SERVICE_AUTH_SECRET is configured.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time

def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip('=')

def make_proof(secret: str, *, audience='veterinaria-aws:/pets/raw', now=None) -> str:
    if len(secret.encode()) < 32:
        raise ValueError('SERVICE_AUTH_SECRET must be >=32 bytes')
    now = int(time.time()) if now is None else int(now)
    claims = {'iss': 'videojuegos-gcp', 'aud': audience, 'iat': now,
              'exp': now + 30, 'jti': secrets.token_hex(16)}
    payload = b64(json.dumps(claims, separators=(',', ':')).encode())
    sig = b64(hmac.new(secret.encode(), f'v1.{payload}'.encode(), hashlib.sha256).digest())
    return f'v1.{payload}.{sig}'

def dependency_headers() -> dict:
    mode = os.getenv('SECURITY_AUTH_MODE', 'off')
    secret = os.getenv('SERVICE_AUTH_SECRET', '')
    if mode == 'off':
        return {}
    if mode == 'baseline':
        return {'x-service-token': secret}
    if mode == 'protected':
        return {'x-service-token': make_proof(secret)}
    raise ValueError('unsupported SECURITY_AUTH_MODE')
