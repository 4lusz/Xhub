"""Utilitarios PKCE para o OAuth 2.0 do X."""

import base64
import hashlib
import secrets


def generate_code_verifier(length: int = 64) -> str:
    if length < 43 or length > 128:
        raise ValueError("code_verifier deve ter entre 43 e 128 caracteres.")

    return secrets.token_urlsafe(length)[:length]


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def generate_state(length: int = 32) -> str:
    return secrets.token_urlsafe(length)
