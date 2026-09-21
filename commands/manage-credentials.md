---
name: manage-credentials
description: Store, check, or clear ENCODE API credentials for restricted data
---

Manage ENCODE API credentials for accessing unreleased or restricted datasets.

Use `encode_manage_credentials` with action "store" to save credentials (needs both `access_key` and `secret_key`), "check" to verify configuration, or "clear" to remove stored credentials. Credentials go to your OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker), falling back to a Fernet-encrypted file at `~/.encode_connector/credentials.enc` when no keyring is available.

Most ENCODE data is public and requires no authentication.
