import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import secrets
from typing import Any


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_SALT_BYTES = 16
REFRESH_TOKEN_BYTES = 32
PASSWORD_RESET_TOKEN_BYTES = 32
ACCESS_TOKEN_ALGORITHM = "HS256"
ACCESS_TOKEN_TYPE = "JWT"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    password_hash = _pbkdf2_hash(
        password=password,
        salt=salt,
        iterations=PASSWORD_HASH_ITERATIONS,
    )
    return "$".join(
        (
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            _encode(salt),
            _encode(password_hash),
        )
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, expected_hash_text = password_hash.split("$", 3)
        iterations = int(iterations_text)
        salt = _decode(salt_text)
        expected_hash = _decode(expected_hash_text)
    except (binascii.Error, ValueError, TypeError):
        return False

    if algorithm != PASSWORD_HASH_ALGORITHM:
        return False

    actual_hash = _pbkdf2_hash(
        password=password,
        salt=salt,
        iterations=iterations,
    )
    return secrets.compare_digest(actual_hash, expected_hash)


def create_access_token(
    *,
    subject: str,
    secret_key: str,
    expires_delta: timedelta,
    claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = dict(claims or {})
    payload.update({
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    })

    header = {"alg": ACCESS_TOKEN_ALGORITHM, "typ": ACCESS_TOKEN_TYPE}
    signing_input = ".".join(
        (
            _encode_json(header),
            _encode_json(payload),
        )
    )
    signature = _sign_token(signing_input, secret_key)
    return f"{signing_input}.{signature}"


def decode_access_token(token: str, *, secret_key: str) -> dict[str, Any] | None:
    try:
        header_text, payload_text, signature = token.split(".", 2)
        signing_input = f"{header_text}.{payload_text}"
        expected_signature = _sign_token(signing_input, secret_key)
        if not secrets.compare_digest(signature, expected_signature):
            return None

        header = json.loads(_decode(header_text))
        payload = json.loads(_decode(payload_text))
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None

    if header.get("alg") != ACCESS_TOKEN_ALGORITHM or header.get("typ") != ACCESS_TOKEN_TYPE:
        return None
    if not isinstance(payload.get("exp"), int):
        return None
    if payload["exp"] < int(datetime.now(timezone.utc).timestamp()):
        return None

    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(REFRESH_TOKEN_BYTES)


def generate_otp(length: int = 6) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_password_reset_token() -> str:
    return secrets.token_urlsafe(PASSWORD_RESET_TOKEN_BYTES)


def hash_refresh_token(refresh_token: str, *, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode("utf-8"),
        refresh_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def hash_token(token: str, *, secret_key: str) -> str:
    return hash_refresh_token(token, secret_key=secret_key)


def validate_password_policy(password: str, *, min_length: int = 8) -> list[str]:
    errors: list[str] = []
    if len(password) < min_length:
        errors.append(f"password must be at least {min_length} characters")
    if password != password.strip():
        errors.append("password must not start or end with whitespace")
    if not any(character.islower() for character in password):
        errors.append("password must include a lowercase letter")
    if not any(character.isupper() for character in password):
        errors.append("password must include an uppercase letter")
    if not any(character.isdigit() for character in password):
        errors.append("password must include a number")
    if not any(not character.isalnum() for character in password):
        errors.append("password must include a symbol")
    return errors


def _pbkdf2_hash(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    padded_value = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded_value.encode("ascii"))


def _encode_json(value: dict[str, Any]) -> str:
    return _encode(
        json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )


def _sign_token(signing_input: str, secret_key: str) -> str:
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _encode(signature)
