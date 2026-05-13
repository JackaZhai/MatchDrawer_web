"""RSA helper for frontend-encrypted login credentials."""

from __future__ import annotations

import base64
import binascii
from typing import Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from ..utils.errors import AuthenticationError


class LoginCryptoService:
    """Manage an in-memory RSA keypair for login payload encryption."""

    def __init__(self) -> None:
        self._private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self._public_key_pem = (
            self._private_key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode("utf-8")
        )

    def get_public_key_pem(self) -> str:
        return self._public_key_pem

    def decrypt(self, ciphertext: str) -> str:
        raw_value = str(ciphertext or "").strip()
        if not raw_value:
            raise AuthenticationError("登录凭证不能为空")

        payload = self._decode_ciphertext(raw_value)
        try:
            plaintext = self._private_key.decrypt(
                payload,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except Exception as exc:
            raise AuthenticationError("登录凭证解密失败") from exc

        try:
            return plaintext.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AuthenticationError("登录凭证编码无效") from exc

    @staticmethod
    def _decode_ciphertext(value: str) -> bytes:
        try:
            return bytes.fromhex(value)
        except ValueError:
            pass

        try:
            return base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise AuthenticationError("登录凭证格式无效") from exc


_login_crypto_service: Optional[LoginCryptoService] = None


def get_login_crypto_service() -> LoginCryptoService:
    global _login_crypto_service
    if _login_crypto_service is None:
        _login_crypto_service = LoginCryptoService()
    return _login_crypto_service
