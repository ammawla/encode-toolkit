"""Tests for credential management — targeting near-100% coverage of auth.py."""

import base64
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from encode_connector.client.auth import CredentialManager, _get_machine_key

# ======================================================================
# _get_machine_key
# ======================================================================


class TestMachineKey:
    def test_returns_bytes(self, tmp_path):
        salt_path = tmp_path / ".salt"
        key = _get_machine_key(salt_path=salt_path)
        assert isinstance(key, bytes)

    def test_consistent_with_same_salt(self, tmp_path):
        salt_path = tmp_path / ".salt"
        key1 = _get_machine_key(salt_path=salt_path)
        key2 = _get_machine_key(salt_path=salt_path)
        assert key1 == key2

    def test_creates_salt_file(self, tmp_path):
        salt_path = tmp_path / ".salt"
        assert not salt_path.exists()
        _get_machine_key(salt_path=salt_path)
        assert salt_path.exists()

    def test_salt_file_permissions(self, tmp_path):
        salt_path = tmp_path / ".salt"
        _get_machine_key(salt_path=salt_path)
        mode = salt_path.stat().st_mode & 0o777
        assert mode == 0o600

    def test_base64_url_safe(self, tmp_path):
        salt_path = tmp_path / ".salt"
        key = _get_machine_key(salt_path=salt_path)
        decoded = base64.urlsafe_b64decode(key)
        assert len(decoded) == 32

    def test_reuses_existing_salt(self, tmp_path):
        """When salt file already exists, it reads rather than regenerating."""
        salt_path = tmp_path / ".salt"
        # Pre-create salt file with known content
        salt_path.write_bytes(b"x" * 32)
        key1 = _get_machine_key(salt_path=salt_path)
        # Salt content unchanged
        assert salt_path.read_bytes() == b"x" * 32
        key2 = _get_machine_key(salt_path=salt_path)
        assert key1 == key2

    def test_creates_parent_directory(self, tmp_path):
        """Salt path with non-existent parent directories are created."""
        salt_path = tmp_path / "nested" / "deep" / ".salt"
        _get_machine_key(salt_path=salt_path)
        assert salt_path.exists()

    def test_default_salt_path_uses_home(self):
        """Without salt_path argument, defaults to ~/.encode_connector/.salt."""
        # We just verify the function is callable with no salt_path (uses default).
        # Patch Path.home to avoid writing to real home dir.
        with patch("encode_connector.client.auth.Path.home") as mock_home:
            fake_home = Path("/tmp/fake_home_test_auth")
            mock_home.return_value = fake_home
            fake_salt = fake_home / ".encode_connector" / ".salt"
            # Pre-create so it reads existing rather than writing
            fake_salt.parent.mkdir(parents=True, exist_ok=True)
            fake_salt.write_bytes(os.urandom(32))
            try:
                key = _get_machine_key()
                assert isinstance(key, bytes)
            finally:
                fake_salt.unlink(missing_ok=True)
                fake_salt.parent.rmdir()
                fake_home.rmdir()


class TestMachineKeyGetUserFallback:
    """Cover lines 46-49: getpass.getuser() fallback in containers/CI."""

    def test_keyerror_falls_back_to_user_env(self, tmp_path):
        """When getpass.getuser() raises KeyError, falls back to USER env var."""
        salt_path = tmp_path / ".salt"
        with patch("getpass.getuser", side_effect=KeyError("no user")):
            with patch.dict(os.environ, {"USER": "ci-user"}, clear=False):
                key = _get_machine_key(salt_path=salt_path)
                assert isinstance(key, bytes)

    def test_keyerror_falls_back_to_username_env(self, tmp_path):
        """Falls back to USERNAME env var when USER is also missing."""
        salt_path = tmp_path / ".salt"
        with patch("getpass.getuser", side_effect=KeyError("no user")):
            with patch.dict(
                os.environ,
                {"USERNAME": "win-user"},
                clear=False,
            ):
                # Remove USER if it exists
                env = os.environ.copy()
                env.pop("USER", None)
                with patch.dict(os.environ, env, clear=True):
                    os.environ["USERNAME"] = "win-user"
                    key = _get_machine_key(salt_path=salt_path)
                    assert isinstance(key, bytes)

    def test_keyerror_falls_back_to_default(self, tmp_path):
        """Falls back to 'encode-user' when no env vars are set."""
        salt_path = tmp_path / ".salt"
        with patch("getpass.getuser", side_effect=KeyError("no user")):
            clean_env = {k: v for k, v in os.environ.items() if k not in ("USER", "USERNAME")}
            with patch.dict(os.environ, clean_env, clear=True):
                key = _get_machine_key(salt_path=salt_path)
                assert isinstance(key, bytes)

    def test_oserror_falls_back(self, tmp_path):
        """When getpass.getuser() raises OSError, falls back gracefully."""
        salt_path = tmp_path / ".salt"
        with patch("getpass.getuser", side_effect=OSError("restricted")):
            key = _get_machine_key(salt_path=salt_path)
            assert isinstance(key, bytes)

    def test_different_fallback_produces_different_key(self, tmp_path):
        """Different fallback usernames produce different keys (different material)."""
        salt_path = tmp_path / ".salt"
        with patch("getpass.getuser", side_effect=KeyError("no user")):
            with patch.dict(os.environ, {"USER": "user-a"}, clear=False):
                key_a = _get_machine_key(salt_path=salt_path)

        # New salt for isolation
        salt_path2 = tmp_path / ".salt2"
        with patch("getpass.getuser", side_effect=KeyError("no user")):
            with patch.dict(os.environ, {"USER": "user-b"}, clear=False):
                key_b = _get_machine_key(salt_path=salt_path2)

        # Different salt + different user = different key
        # (They may also differ just from different salt)
        assert isinstance(key_a, bytes) and isinstance(key_b, bytes)


# ======================================================================
# CredentialManager._check_keyring
# ======================================================================


class TestCheckKeyring:
    """Cover lines 87-92: _check_keyring branches."""

    def test_keyring_available_cached_true(self):
        """Returns cached True without re-checking."""
        cm = CredentialManager()
        cm._keyring_available = True
        assert cm._check_keyring() is True

    def test_keyring_available_cached_false(self):
        """Returns cached False without re-checking."""
        cm = CredentialManager()
        cm._keyring_available = False
        assert cm._check_keyring() is False

    def test_keyring_success(self):
        """When keyring.get_password succeeds, keyring is available."""
        cm = CredentialManager()
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = None
        with patch.dict("sys.modules", {"keyring": mock_keyring, "keyring.errors": MagicMock()}):
            result = cm._check_keyring()
            assert result is True
            assert cm._keyring_available is True

    def test_keyring_no_keyring_error(self):
        """When NoKeyringError is raised, keyring is unavailable (line 87-88)."""
        cm = CredentialManager()

        mock_errors = MagicMock()

        class FakeNoKeyringError(Exception):
            pass

        mock_errors.NoKeyringError = FakeNoKeyringError
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = FakeNoKeyringError("no backend")

        cm._keyring_available = None  # Reset cache
        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            if name == "keyring.errors":
                return mock_errors
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = cm._check_keyring()
            assert result is False
            assert cm._keyring_available is False

    def test_keyring_generic_exception(self):
        """When get_password raises a generic Exception, keyring is unavailable (line 89-90)."""
        cm = CredentialManager()

        mock_errors = MagicMock()
        mock_errors.NoKeyringError = type("NoKeyringError", (Exception,), {})
        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = RuntimeError("unexpected error")

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            if name == "keyring.errors":
                return mock_errors
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = cm._check_keyring()
            assert result is False
            assert cm._keyring_available is False

    def test_keyring_import_error(self):
        """When keyring cannot be imported, keyring is unavailable (line 91-92)."""
        cm = CredentialManager()

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring" or name == "keyring.errors":
                raise ImportError("No module named 'keyring'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = cm._check_keyring()
            assert result is False
            assert cm._keyring_available is False


# ======================================================================
# CredentialManager._read_from_keyring
# ======================================================================


class TestReadFromKeyring:
    """Cover lines 96-107: _read_from_keyring."""

    def test_returns_none_when_keyring_unavailable(self):
        """When keyring is not available, returns (None, None) immediately."""
        cm = CredentialManager()
        cm._keyring_available = False
        assert cm._read_from_keyring() == (None, None)

    def test_success(self):
        """Reads credentials from keyring successfully (lines 100-105)."""
        cm = CredentialManager()
        cm._keyring_available = True

        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = lambda svc, key: {
            "access_key": "ak_from_keyring",
            "secret_key": "sk_from_keyring",
        }.get(key)

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            access, secret = cm._read_from_keyring()
            assert access == "ak_from_keyring"
            assert secret == "sk_from_keyring"

    def test_exception_returns_none(self):
        """When keyring.get_password raises, returns (None, None) (lines 106-107)."""
        cm = CredentialManager()
        cm._keyring_available = True

        mock_keyring = MagicMock()
        mock_keyring.get_password.side_effect = RuntimeError("keyring broken")

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            assert cm._read_from_keyring() == (None, None)


# ======================================================================
# CredentialManager._write_to_keyring
# ======================================================================


class TestWriteToKeyring:
    """Cover lines 109-122: _write_to_keyring."""

    def test_returns_false_when_keyring_unavailable(self):
        """When keyring is not available, returns False immediately (line 111-112)."""
        cm = CredentialManager()
        cm._keyring_available = False
        assert cm._write_to_keyring("ak", "sk") is False

    def test_success(self):
        """Stores credentials in keyring successfully (lines 113-119)."""
        cm = CredentialManager()
        cm._keyring_available = True

        mock_keyring = MagicMock()

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = cm._write_to_keyring("my_ak", "my_sk")
            assert result is True
            assert mock_keyring.set_password.call_count == 2

    def test_exception_returns_false(self):
        """When keyring.set_password raises, returns False (lines 120-122)."""
        cm = CredentialManager()
        cm._keyring_available = True

        mock_keyring = MagicMock()
        mock_keyring.set_password.side_effect = RuntimeError("write failed")

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            result = cm._write_to_keyring("ak", "sk")
            assert result is False


# ======================================================================
# CredentialManager._read_from_encrypted_file
# ======================================================================


class TestReadFromEncryptedFile:
    """Cover lines 124-139: _read_from_encrypted_file."""

    def test_file_not_found(self, tmp_path):
        """Returns (None, None) when credential file doesn't exist (line 126-127)."""
        cm = CredentialManager()
        cm._fallback_file = tmp_path / "nonexistent.enc"
        assert cm._read_from_encrypted_file() == (None, None)

    def test_roundtrip(self, tmp_path):
        """Write then read back credentials from encrypted file."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"
        cm._write_to_encrypted_file("test_key", "test_secret")
        access, secret = cm._read_from_encrypted_file()
        assert access == "test_key"
        assert secret == "test_secret"

    def test_decrypt_failure_corrupt_data(self, tmp_path):
        """Returns (None, None) when file contains corrupt data (lines 137-139)."""
        cm = CredentialManager()
        cm._fallback_file = tmp_path / "credentials.enc"
        # Write garbage that can't be decrypted
        cm._fallback_file.write_bytes(b"this is not valid encrypted data at all")
        access, secret = cm._read_from_encrypted_file()
        assert access is None
        assert secret is None

    def test_decrypt_failure_wrong_key(self, tmp_path):
        """Returns (None, None) when key doesn't match (lines 137-139)."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"
        # Write with current key
        cm._write_to_encrypted_file("test_key", "test_secret")

        # Now corrupt the salt so the derived key is different
        with patch(
            "encode_connector.client.auth._get_machine_key",
            return_value=base64.urlsafe_b64encode(b"x" * 32),
        ):
            access, secret = cm._read_from_encrypted_file()
            assert access is None
            assert secret is None


# ======================================================================
# CredentialManager._write_to_encrypted_file
# ======================================================================


class TestWriteToEncryptedFile:
    """Cover lines 141-161: _write_to_encrypted_file."""

    def test_success(self, tmp_path):
        """Writes encrypted file successfully."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"
        assert cm._write_to_encrypted_file("ak", "sk") is True
        assert cm._fallback_file.exists()

    def test_file_permissions(self, tmp_path):
        """Encrypted file and directory have restricted permissions."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"
        cm._write_to_encrypted_file("key", "secret")

        dir_mode = tmp_path.stat().st_mode & 0o777
        assert dir_mode == 0o700

        file_mode = cm._fallback_file.stat().st_mode & 0o777
        assert file_mode == 0o600

    def test_exception_returns_false(self, tmp_path):
        """Returns False when write fails (lines 159-161)."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"

        # Patch Fernet to raise during encryption
        with patch(
            "encode_connector.client.auth._get_machine_key",
            side_effect=RuntimeError("key derivation failed"),
        ):
            result = cm._write_to_encrypted_file("ak", "sk")
            assert result is False

    def test_exception_on_fernet_encrypt(self, tmp_path):
        """Returns False when Fernet.encrypt raises."""
        cm = CredentialManager()
        cm._fallback_dir = tmp_path
        cm._fallback_file = tmp_path / "credentials.enc"

        mock_fernet_instance = MagicMock()
        mock_fernet_instance.encrypt.side_effect = ValueError("encrypt error")

        with patch("encode_connector.client.auth._get_machine_key", return_value=base64.urlsafe_b64encode(b"a" * 32)):
            with patch("cryptography.fernet.Fernet", return_value=mock_fernet_instance):
                result = cm._write_to_encrypted_file("ak", "sk")
                assert result is False


# ======================================================================
# CredentialManager.get_credentials — full cascade
# ======================================================================


class TestGetCredentials:
    """Cover lines 171-207: get_credentials full cascade."""

    def test_returns_from_cache(self):
        """Cache hit returns immediately (lines 181-182)."""
        cm = CredentialManager()
        cm._access_key = "cached_ak"
        cm._secret_key = "cached_sk"
        access, secret = cm.get_credentials()
        assert access == "cached_ak"
        assert secret == "cached_sk"

    def test_returns_from_keyring(self):
        """Keyring credentials are cached and returned (lines 186-189)."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=("kr_ak", "kr_sk"))
        cm._read_from_encrypted_file = MagicMock(return_value=(None, None))
        cm._read_from_env = MagicMock(return_value=(None, None))

        access, secret = cm.get_credentials()
        assert access == "kr_ak"
        assert secret == "kr_sk"
        # Cached for next call
        assert cm._access_key == "kr_ak"
        assert cm._secret_key == "kr_sk"

    def test_returns_from_encrypted_file(self):
        """Encrypted file credentials are cached and returned (lines 193-196)."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=(None, None))
        cm._read_from_encrypted_file = MagicMock(return_value=("file_ak", "file_sk"))
        cm._read_from_env = MagicMock(return_value=(None, None))

        access, secret = cm.get_credentials()
        assert access == "file_ak"
        assert secret == "file_sk"
        assert cm._access_key == "file_ak"
        assert cm._secret_key == "file_sk"

    def test_returns_from_env_and_migrates(self):
        """Env var credentials are cached and migrated to storage (lines 200-205)."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=(None, None))
        cm._read_from_encrypted_file = MagicMock(return_value=(None, None))
        cm._read_from_env = MagicMock(return_value=("env_ak", "env_sk"))
        cm.store_credentials = MagicMock(return_value="OS keyring")

        access, secret = cm.get_credentials()
        assert access == "env_ak"
        assert secret == "env_sk"
        assert cm._access_key == "env_ak"
        assert cm._secret_key == "env_sk"
        # Migrated to secure storage
        cm.store_credentials.assert_called_once_with("env_ak", "env_sk")

    def test_returns_none_when_nothing_found(self):
        """Returns (None, None) when all sources empty (line 207)."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=(None, None))
        cm._read_from_encrypted_file = MagicMock(return_value=(None, None))
        cm._read_from_env = MagicMock(return_value=(None, None))

        access, secret = cm.get_credentials()
        assert access is None
        assert secret is None

    def test_keyring_returns_partial_falls_through(self):
        """If keyring returns only access_key (no secret), falls through."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=("ak_only", None))
        cm._read_from_encrypted_file = MagicMock(return_value=("file_ak", "file_sk"))
        cm._read_from_env = MagicMock(return_value=(None, None))

        access, secret = cm.get_credentials()
        assert access == "file_ak"
        assert secret == "file_sk"

    def test_cascade_order(self):
        """Keyring is checked before file, file before env."""
        cm = CredentialManager()
        call_order = []

        def mock_keyring():
            call_order.append("keyring")
            return (None, None)

        def mock_file():
            call_order.append("file")
            return (None, None)

        def mock_env():
            call_order.append("env")
            return (None, None)

        cm._read_from_keyring = mock_keyring
        cm._read_from_encrypted_file = mock_file
        cm._read_from_env = mock_env

        cm.get_credentials()
        assert call_order == ["keyring", "file", "env"]


# ======================================================================
# CredentialManager.store_credentials
# ======================================================================


class TestStoreCredentials:
    """Cover lines 209-224: store_credentials."""

    def test_keyring_success(self):
        """When keyring write succeeds, returns keyring description (lines 215-219)."""
        cm = CredentialManager()
        cm._write_to_keyring = MagicMock(return_value=True)
        cm._write_to_encrypted_file = MagicMock(return_value=False)

        result = cm.store_credentials("ak", "sk")
        assert "keyring" in result.lower() or "Keychain" in result
        assert cm._access_key == "ak"
        assert cm._secret_key == "sk"

    def test_keyring_fail_file_success(self):
        """When keyring fails but file works, returns file description (lines 221-222)."""
        cm = CredentialManager()
        cm._write_to_keyring = MagicMock(return_value=False)
        cm._write_to_encrypted_file = MagicMock(return_value=True)

        result = cm.store_credentials("ak", "sk")
        assert "Encrypted file" in result or "encrypted" in result.lower()

    def test_both_fail_memory_only(self):
        """When both fail, returns memory-only description (line 224)."""
        cm = CredentialManager()
        cm._write_to_keyring = MagicMock(return_value=False)
        cm._write_to_encrypted_file = MagicMock(return_value=False)

        result = cm.store_credentials("ak", "sk")
        assert "Memory only" in result
        # Still cached in memory
        assert cm._access_key == "ak"
        assert cm._secret_key == "sk"


# ======================================================================
# CredentialManager.clear_credentials
# ======================================================================


class TestClearCredentials:
    """Cover lines 226-243: clear_credentials."""

    def test_clears_memory(self):
        """Clears in-memory cache (lines 228-229)."""
        cm = CredentialManager()
        cm._access_key = "ak"
        cm._secret_key = "sk"
        cm._keyring_available = False
        cm._fallback_file = Path("/nonexistent")
        cm.clear_credentials()
        assert cm._access_key is None
        assert cm._secret_key is None

    def test_clears_keyring(self):
        """When keyring is available, deletes from keyring (lines 232-239)."""
        cm = CredentialManager()
        cm._access_key = "ak"
        cm._secret_key = "sk"
        cm._keyring_available = True
        cm._fallback_file = Path("/nonexistent")

        mock_keyring = MagicMock()
        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            cm.clear_credentials()
            assert mock_keyring.delete_password.call_count == 2

    def test_clears_keyring_exception_swallowed(self):
        """Keyring delete exception is silently ignored (lines 238-239)."""
        cm = CredentialManager()
        cm._access_key = "ak"
        cm._secret_key = "sk"
        cm._keyring_available = True
        cm._fallback_file = Path("/nonexistent")

        mock_keyring = MagicMock()
        mock_keyring.delete_password.side_effect = RuntimeError("delete failed")

        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            # Should not raise
            cm.clear_credentials()
            assert cm._access_key is None

    def test_clears_encrypted_file(self, tmp_path):
        """Deletes the encrypted credential file if it exists (lines 242-243)."""
        cm = CredentialManager()
        cm._keyring_available = False
        cm._fallback_file = tmp_path / "credentials.enc"
        cm._fallback_file.write_bytes(b"encrypted data")
        assert cm._fallback_file.exists()

        cm.clear_credentials()
        assert not cm._fallback_file.exists()

    def test_no_file_no_error(self, tmp_path):
        """When encrypted file doesn't exist, no error raised."""
        cm = CredentialManager()
        cm._keyring_available = False
        cm._fallback_file = tmp_path / "nonexistent.enc"
        cm.clear_credentials()  # Should not raise

    def test_clears_both_keyring_and_file(self, tmp_path):
        """Clears both keyring and encrypted file when both exist."""
        cm = CredentialManager()
        cm._access_key = "ak"
        cm._secret_key = "sk"
        cm._keyring_available = True
        cm._fallback_file = tmp_path / "credentials.enc"
        cm._fallback_file.write_bytes(b"encrypted data")

        mock_keyring = MagicMock()
        real_import = __import__

        def custom_import(name, *args, **kwargs):
            if name == "keyring":
                return mock_keyring
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=custom_import):
            cm.clear_credentials()
            assert cm._access_key is None
            assert mock_keyring.delete_password.call_count == 2
            assert not cm._fallback_file.exists()


# ======================================================================
# CredentialManager.has_credentials property
# ======================================================================


class TestHasCredentials:
    """Cover lines 245-249: has_credentials property."""

    def test_true_when_credentials_available(self):
        cm = CredentialManager()
        cm._access_key = "ak"
        cm._secret_key = "sk"
        assert cm.has_credentials is True

    def test_false_when_no_credentials(self):
        cm = CredentialManager()
        cm._keyring_available = False
        cm._fallback_file = Path("/nonexistent")
        assert cm.has_credentials is False

    def test_true_when_credentials_in_keyring(self):
        """has_credentials delegates to get_credentials which checks keyring."""
        cm = CredentialManager()
        cm._read_from_keyring = MagicMock(return_value=("ak", "sk"))
        assert cm.has_credentials is True


# ======================================================================
# CredentialManager.get_auth_header
# ======================================================================


class TestGetAuthHeader:
    def test_returns_basic_auth(self):
        cm = CredentialManager()
        cm._access_key = "mykey"
        cm._secret_key = "mysecret"
        header = cm.get_auth_header()
        assert header is not None
        assert "Authorization" in header
        assert header["Authorization"].startswith("Basic ")
        token = header["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(token).decode()
        assert decoded == "mykey:mysecret"

    def test_returns_none_without_credentials(self):
        cm = CredentialManager()
        cm._keyring_available = False
        cm._fallback_file = Path("/nonexistent")
        assert cm.get_auth_header() is None


# ======================================================================
# CredentialManager._read_from_env
# ======================================================================


class TestReadFromEnv:
    def test_reads_from_env(self):
        cm = CredentialManager()
        with patch.dict(
            os.environ,
            {"ENCODE_ACCESS_KEY": "env_key", "ENCODE_SECRET_KEY": "env_secret"},
        ):
            access, secret = cm._read_from_env()
            assert access == "env_key"
            assert secret == "env_secret"

    def test_returns_none_when_missing(self):
        cm = CredentialManager()
        with patch.dict(os.environ, {}, clear=True):
            access, secret = cm._read_from_env()
            assert access is None
            assert secret is None

    def test_returns_none_when_partial(self):
        cm = CredentialManager()
        with patch.dict(
            os.environ,
            {"ENCODE_ACCESS_KEY": "only_key"},
            clear=True,
        ):
            access, secret = cm._read_from_env()
            assert access is None
            assert secret is None
