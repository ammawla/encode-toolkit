"""Secure credential management for ENCODE API authentication.

Credentials are stored in the OS keyring (macOS Keychain, Linux Secret Service,
Windows Credential Locker). Falls back to Fernet-encrypted file storage when
keyring is unavailable.

Credentials never appear in logs, error messages, or are sent anywhere
except the ENCODE API over HTTPS.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import platform
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_machine_key(salt_path: Path | None = None) -> bytes:
    """Derive a machine-specific encryption key for fallback file storage.

    Uses PBKDF2 with a random salt stored alongside the credentials file.
    The salt is generated once and reused for subsequent key derivations.
    """
    if salt_path is None:
        salt_path = Path.home() / ".encode_connector" / ".salt"

    # Generate or read the salt
    if salt_path.exists():
        salt = salt_path.read_bytes()
    else:
        salt_path.parent.mkdir(parents=True, exist_ok=True)
        salt = os.urandom(32)
        salt_path.write_bytes(salt)
        salt_path.chmod(0o600)

    # Combine machine-specific values as key material
    import getpass

    try:
        login = getpass.getuser()
    except (KeyError, OSError):
        # getpass.getuser() raises KeyError in containers/CI where the user
        # is not in the password database, or OSError in restricted environments
        login = os.environ.get("USER", os.environ.get("USERNAME", "encode-user"))
    material = f"{platform.node()}-{login}-encode-connector"

    # Use PBKDF2 with 600,000 iterations (OWASP recommendation)
    dk = hashlib.pbkdf2_hmac("sha256", material.encode(), salt, 600_000, dklen=32)
    return base64.urlsafe_b64encode(dk)


class CredentialManager:
    """Manages ENCODE API credentials with secure storage.

    Storage priority:
    1. OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker)
    2. Fernet-encrypted file at ~/.encode_connector/credentials.enc
    3. Environment variables (read-only, for initial setup)
    """

    SERVICE_NAME = "encode-connector"
    _fallback_dir = Path.home() / ".encode_connector"
    _fallback_file = _fallback_dir / "credentials.enc"

    def __init__(self) -> None:
        self._access_key: str | None = None
        self._secret_key: str | None = None
        self._keyring_available: bool | None = None

    def _check_keyring(self) -> bool:
        """Check if OS keyring is available."""
        if self._keyring_available is not None:
            return self._keyring_available
        try:
            import keyring
            from keyring.errors import NoKeyringError

            try:
                # Test keyring access
                keyring.get_password(self.SERVICE_NAME, "__test__")
                self._keyring_available = True
            except NoKeyringError:
                self._keyring_available = False
            except Exception:
                self._keyring_available = False
        except ImportError:
            self._keyring_available = False

        return self._keyring_available

    def _read_from_keyring(self) -> tuple[str | None, str | None]:
        """Read credentials from OS keyring."""
        if not self._check_keyring():
            return None, None
        try:
            import keyring

            access_key = keyring.get_password(self.SERVICE_NAME, "access_key")
            secret_key = keyring.get_password(self.SERVICE_NAME, "secret_key")
            return access_key, secret_key
        except Exception:
            return None, None

    def _write_to_keyring(self, access_key: str, secret_key: str) -> bool:
        """Store credentials in OS keyring. Returns True on success."""
        if not self._check_keyring():
            return False
        try:
            import keyring

            keyring.set_password(self.SERVICE_NAME, "access_key", access_key)
            keyring.set_password(self.SERVICE_NAME, "secret_key", secret_key)
            logger.info("Credentials stored in OS keyring")
            return True
        except Exception as e:
            logger.warning("Failed to store credentials in keyring: %s", type(e).__name__)
            return False

    def _read_from_encrypted_file(self) -> tuple[str | None, str | None]:
        """Read credentials from Fernet-encrypted file."""
        if not self._fallback_file.exists():
            return None, None
        try:
            from cryptography.fernet import Fernet

            key = _get_machine_key()
            f = Fernet(key)
            data = f.decrypt(self._fallback_file.read_bytes()).decode()
            parts = data.split("\n", 1)
            if len(parts) == 2:
                return parts[0], parts[1]
        except Exception:
            logger.warning("Failed to decrypt credential file")
        return None, None

    def _write_to_encrypted_file(self, access_key: str, secret_key: str) -> bool:
        """Store credentials in Fernet-encrypted file."""
        try:
            from cryptography.fernet import Fernet

            self._fallback_dir.mkdir(parents=True, exist_ok=True)
            # Restrict directory permissions
            self._fallback_dir.chmod(0o700)

            key = _get_machine_key()
            f = Fernet(key)
            data = f"{access_key}\n{secret_key}"
            encrypted = f.encrypt(data.encode())
            self._fallback_file.write_bytes(encrypted)
            # Restrict file permissions
            self._fallback_file.chmod(0o600)
            logger.info("Credentials stored in encrypted file")
            return True
        except Exception as e:
            logger.warning("Failed to write encrypted credential file: %s", type(e).__name__)
            return False

    def _read_from_env(self) -> tuple[str | None, str | None]:
        """Read credentials from environment variables."""
        access_key = os.environ.get("ENCODE_ACCESS_KEY")
        secret_key = os.environ.get("ENCODE_SECRET_KEY")
        if access_key and secret_key:
            return access_key, secret_key
        return None, None

    def get_credentials(self) -> tuple[str | None, str | None]:
        """Get ENCODE API credentials from the most secure available source.

        Checks in order: cache -> keyring -> encrypted file -> env vars.
        If found in env vars, migrates to keyring/encrypted file for future use.

        Returns:
            Tuple of (access_key, secret_key), both None if no credentials found.
        """
        # Check cache first
        if self._access_key and self._secret_key:
            return self._access_key, self._secret_key

        # Try keyring
        access_key, secret_key = self._read_from_keyring()
        if access_key and secret_key:
            self._access_key = access_key
            self._secret_key = secret_key
            return access_key, secret_key

        # Try encrypted file
        access_key, secret_key = self._read_from_encrypted_file()
        if access_key and secret_key:
            self._access_key = access_key
            self._secret_key = secret_key
            return access_key, secret_key

        # Try env vars (and migrate to secure storage)
        access_key, secret_key = self._read_from_env()
        if access_key and secret_key:
            self._access_key = access_key
            self._secret_key = secret_key
            # Migrate to secure storage
            self.store_credentials(access_key, secret_key)
            return access_key, secret_key

        return None, None

    def store_credentials(self, access_key: str, secret_key: str) -> str:
        """Store credentials in the most secure available storage.

        Returns:
            Description of where credentials were stored.
        """
        self._access_key = access_key
        self._secret_key = secret_key

        if self._write_to_keyring(access_key, secret_key):
            return "OS keyring (macOS Keychain / Linux Secret Service / Windows Credential Locker)"

        if self._write_to_encrypted_file(access_key, secret_key):
            return f"Encrypted file ({self._fallback_file})"

        return "Memory only (credentials will not persist across sessions)"

    def clear_credentials(self) -> None:
        """Remove all stored credentials."""
        self._access_key = None
        self._secret_key = None

        # Clear keyring
        if self._check_keyring():
            try:
                import keyring

                keyring.delete_password(self.SERVICE_NAME, "access_key")
                keyring.delete_password(self.SERVICE_NAME, "secret_key")
            except Exception:
                pass

        # Clear encrypted file
        if self._fallback_file.exists():
            self._fallback_file.unlink()

    @property
    def has_credentials(self) -> bool:
        """Check if credentials are available without revealing them."""
        access_key, secret_key = self.get_credentials()
        return bool(access_key and secret_key)

    def get_auth_header(self) -> dict[str, str] | None:
        """Get HTTP Basic auth header for ENCODE API.

        Returns:
            Dict with Authorization header, or None if no credentials.
        """
        access_key, secret_key = self.get_credentials()
        if not access_key or not secret_key:
            return None

        token = base64.b64encode(f"{access_key}:{secret_key}".encode()).decode()
        return {"Authorization": f"Basic {token}"}
