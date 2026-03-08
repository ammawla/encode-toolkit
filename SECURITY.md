# Security Policy

The ENCODE Toolkit plugin is committed to protecting user data and maintaining secure interactions with the ENCODE Project API. This document outlines our vulnerability disclosure policy and security practices.

## Supported Versions

| Version | Status |
|---------|--------|
| v0.2.x  | Currently supported — receives security patches |
| v0.1.x  | No longer supported — please upgrade |

## Reporting a Vulnerability

**Email:** ammawla@ucdavis.edu

Please do **NOT** open public GitHub issues for security vulnerabilities. Responsible disclosure via email ensures that fixes can be developed before details become public.

### What to Include

- A clear description of the vulnerability
- Steps to reproduce the issue
- An assessment of the potential impact (e.g., data exposure, credential leak, remote code execution)
- The affected version(s) of the plugin
- Any suggested mitigations or fixes, if available

### Response Timeline

| Milestone              | Target     |
|------------------------|------------|
| Acknowledgment         | 48 hours   |
| Initial assessment     | 7 days     |
| Fix or mitigation      | 30 days    |
| Public disclosure       | After fix is released |

We will coordinate disclosure timing with the reporter. If a fix requires more than 30 days, we will provide status updates at regular intervals.

## Scope

### In Scope

- **ENCODE API interaction security** — SSRF, request injection, response handling
- **Credential handling** — OS keyring storage, encrypted fallback via Fernet
- **Input validation** — accession format enforcement, path traversal prevention, SQL injection
- **SQLite tracker data integrity** — parameterized queries, schema enforcement
- **File download security** — URL allowlisting to encodeproject.org, MD5 verification
- **MCP transport security** — message validation, tool parameter sanitization

### Out of Scope

- **The ENCODE Project API itself** — report to encode-help@lists.stanford.edu
- **Third-party dependency vulnerabilities** — report to the respective package maintainers
- **Issues in the MCP SDK** — report to Anthropic

## Security Architecture

The plugin implements defense-in-depth across multiple layers. For the full OWASP MCP Top 10 compliance mapping, see `docs/security.md`.

**Key controls:**

- **Input validation** — All user-supplied parameters (accession IDs, file paths, query terms) are validated and sanitized before any API call or database operation.
- **Credential storage** — API credentials are stored in the OS keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker). An encrypted fallback using Fernet is available when keyring access is unavailable.
- **Parameterized SQL** — All SQLite queries use parameterized statements to prevent injection.
- **Download allowlisting** — File downloads are restricted to encodeproject.org domains, with MD5 checksum verification on all downloaded files.
- **Rate limiting** — API requests are throttled to respect ENCODE's rate limits and prevent abuse.

## Recognition

We appreciate responsible disclosure from the security community. With the reporter's permission, we will credit vulnerability reporters in the corresponding release notes.

## Contact

**Maintainer:** Dr. Alex M. Mawla, PhD
**Security reports:** ammawla@ucdavis.edu
