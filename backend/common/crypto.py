"""Encryption at rest for the device's private text (chat history, audit arguments).

What this protects, precisely: AES-256-GCM with a random 96-bit nonce per value. The 256-bit
key lives next to the device data in `device.key`; on Windows it is wrapped with DPAPI (tied
to the signed-in OS user), elsewhere the file is created with mode 0600.

What it does NOT protect: the Qdrant Edge shard files are plain on disk (Edge has no
encryption option), so full-disk encryption (BitLocker / FileVault / LUKS) is still the answer
for a lost laptop. Documented in the README under Limitations.
"""
import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIX = "enc1:"


def _wrap(key: bytes) -> bytes:
    try:
        import win32crypt  # type: ignore

        return b"dpapi:" + win32crypt.CryptProtectData(key, "smaran", None, None, None, 0)
    except Exception:  # noqa: BLE001  not Windows, or pywin32 missing
        return b"raw:" + key


def _unwrap(blob: bytes) -> bytes:
    if blob.startswith(b"dpapi:"):
        import win32crypt  # type: ignore

        return win32crypt.CryptUnprotectData(blob[6:], None, None, None, 0)[1]
    return blob[4:]


class Vault:
    def __init__(self, key_path: Path):
        key_path.parent.mkdir(parents=True, exist_ok=True)
        if key_path.exists():
            key = _unwrap(key_path.read_bytes())
        else:
            key = AESGCM.generate_key(bit_length=256)
            key_path.write_bytes(_wrap(key))
            try:
                os.chmod(key_path, 0o600)
            except OSError:
                pass
        self.protection = "dpapi" if key_path.read_bytes().startswith(b"dpapi:") else "file-0600"
        self._aes = AESGCM(key)

    def seal(self, text: str) -> str:
        nonce = os.urandom(12)
        return PREFIX + base64.b64encode(nonce + self._aes.encrypt(nonce, text.encode("utf8"), None)).decode()

    def open(self, blob: str) -> str:
        if not blob.startswith(PREFIX):
            return blob                      # written before encryption was on
        raw = base64.b64decode(blob[len(PREFIX):])
        return self._aes.decrypt(raw[:12], raw[12:], None).decode("utf8")
