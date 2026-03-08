# ENCODE MCP Security Compliance

*Author: Dr. Alex M. Mawla, PhD*

This document maps the ENCODE MCP server's security controls against the two authoritative MCP security frameworks:

1. **OWASP MCP Top 10 (2025)** -- the industry standard for MCP server security risks
2. **MCP Specification Security Best Practices** -- the official security guidance from the Model Context Protocol specification

Each section states the risk, our mitigation, and the specific code implementing it.

---

## Table of Contents

- [OWASP MCP Top 10 Compliance](#owasp-mcp-top-10-compliance)
  - [MCP01 -- Token Mismanagement & Secret Exposure](#mcp012025----token-mismanagement--secret-exposure)
  - [MCP02 -- Privilege Escalation via Scope Creep](#mcp022025----privilege-escalation-via-scope-creep)
  - [MCP03 -- Tool Poisoning](#mcp032025----tool-poisoning)
  - [MCP04 -- Software Supply Chain Attacks](#mcp042025----software-supply-chain-attacks)
  - [MCP05 -- Command Injection & Execution](#mcp052025----command-injection--execution)
  - [MCP06 -- Intent Flow Subversion](#mcp062025----intent-flow-subversion)
  - [MCP07 -- Insufficient Authentication & Authorization](#mcp072025----insufficient-authentication--authorization)
  - [MCP08 -- Lack of Audit and Telemetry](#mcp082025----lack-of-audit-and-telemetry)
  - [MCP09 -- Shadow MCP Servers](#mcp092025----shadow-mcp-servers)
  - [MCP10 -- Context Injection & Over-Sharing](#mcp102025----context-injection--over-sharing)
- [MCP Specification Best Practices](#mcp-specification-best-practices)
  - [SSRF Prevention](#ssrf-prevention)
  - [Transport Security](#transport-security)
  - [Input Validation](#input-validation)
- [Additional Security Controls](#additional-security-controls)
  - [SQL Injection Prevention](#sql-injection-prevention)
  - [Path Traversal Prevention](#path-traversal-prevention)
  - [Rate Limiting](#rate-limiting)
  - [Download Integrity](#download-integrity)
  - [Concurrency Safety](#concurrency-safety)
- [Security Architecture Summary](#security-architecture-summary)
- [Test Coverage](#test-coverage)
- [References](#references)

---

## OWASP MCP Top 10 Compliance

### MCP01:2025 -- Token Mismanagement & Secret Exposure

> **Risk:** Hard-coded credentials, long-lived tokens, and secrets stored in model memory or protocol logs can expose sensitive environments to unauthorized access.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| No hard-coded credentials | Zero secrets in source code. Verified via `grep -r "password\|secret\|api_key" src/` |
| OS keyring storage | Credentials stored in macOS Keychain / Linux Secret Service / Windows Credential Locker via the `keyring` library (`auth.py`) |
| Encrypted fallback | When OS keyring is unavailable, credentials are encrypted with Fernet using a PBKDF2-derived key (600,000 iterations, random 32-byte salt) (`auth.py::_get_machine_key`) |
| Salt file protection | Salt file created with `0o600` permissions (owner read/write only) at `~/.encode_connector/.salt` |
| Auth header stripping | Credentials are NOT sent to redirect destinations. Download redirects (S3/CDN) receive only a User-Agent header (`downloader.py::_stream_download`) |
| No logging of secrets | Logger uses `logging.getLogger(__name__)` with no `basicConfig`. No credential values are logged at any level |

**Key files:** `auth.py`, `downloader.py`

---

### MCP02:2025 -- Privilege Escalation via Scope Creep

> **Risk:** Loosely defined permissions within MCP servers grant agents excessive capabilities.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| Read-only by default | 14 of 16 tools are read-only (search, list, get, track). No tools modify ENCODE data. |
| Download requires explicit path | Downloads write only to user-specified directories, never to system paths |
| No shell execution | Zero `subprocess`, `os.system`, or `exec` calls anywhere in the codebase |
| No file deletion | No tool deletes files. Provenance logging is append-only |
| Tracker is local-only | SQLite database is local to `~/.encode_connector/`. No network exposure |
| No OAuth scope escalation | Server uses stdio transport (no HTTP endpoint, no OAuth flows) |

**Privilege inventory of all 16 tools:**

| Tool | Reads Network | Writes Disk | Modifies State |
|------|:---:|:---:|:---:|
| `encode_search_experiments` | ENCODE API | -- | -- |
| `encode_get_experiment` | ENCODE API | -- | -- |
| `encode_list_files` | ENCODE API | -- | -- |
| `encode_search_files` | ENCODE API | -- | -- |
| `encode_get_file_info` | ENCODE API | -- | -- |
| `encode_get_metadata` | -- | -- | -- |
| `encode_get_facets` | ENCODE API | -- | -- |
| `encode_download_files` | ENCODE API | User dir | -- |
| `encode_batch_download` | ENCODE API | User dir | -- |
| `encode_manage_credentials` | -- | OS keyring | Client state |
| `encode_track_experiment` | ENCODE API | SQLite | Local DB |
| `encode_list_tracked` | -- | -- | -- |
| `encode_get_citations` | -- | -- | -- |
| `encode_compare_experiments` | -- | -- | -- |
| `encode_log_derived_file` | -- | SQLite | Local DB |
| `encode_get_provenance` | -- | -- | -- |

---

### MCP03:2025 -- Tool Poisoning

> **Risk:** Adversaries compromise tool descriptions to inject malicious instructions that manipulate model behavior.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| Static tool definitions | All 16 tools are defined in source code with fixed docstrings. Tool descriptions never change at runtime |
| No dynamic tool registration | Tools are registered at import time via `@mcp.tool()` decorators. No API for runtime tool creation |
| No tool description from external sources | Descriptions are hardcoded Python docstrings, not loaded from ENCODE API or user input |
| Published source code | Tool definitions are visible and auditable in `server/main.py` |

---

### MCP04:2025 -- Software Supply Chain Attacks

> **Risk:** Compromised dependencies can alter agent behavior or introduce backdoors.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| Minimal dependencies | Core: `httpx`, `mcp[cli]`, `pydantic`, `keyring`. No transitive framework bloat |
| Pinned versions | `pyproject.toml` specifies version constraints |
| No eval/exec | Zero use of `eval()`, `exec()`, `compile()`, or `importlib` on user input |
| No plugin system | No mechanism to load arbitrary code at runtime |
| PyPI distribution | Package distributed via PyPI with standard build tooling |
| Dockerfile uses specific base | Dockerfile pins `python:3.13-slim` |

---

### MCP05:2025 -- Command Injection & Execution

> **Risk:** AI agents construct and execute system commands using untrusted input.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| No shell execution | Zero use of `subprocess`, `os.system`, `os.popen`, `exec`, `eval` |
| Accession validation | All user-supplied accessions validated against `^ENC[A-Z]{2,4}[A-Z0-9]{3,8}$` before use (`validation.py::validate_accession`) |
| Date validation | Date strings validated against `^\d{4}-\d{2}-\d{2}$` (`validation.py::validate_date`) |
| Path validation | API paths validated against `^/[a-zA-Z0-9][a-zA-Z0-9/_@.+-]*/?$` to prevent SSRF (`validation.py::validate_encode_path`) |
| URL validation | Download URLs restricted to allowlisted hosts over HTTPS (`validation.py::validate_download_url`) |
| Lucene escaping | Free-text search terms have special characters escaped before being sent to ENCODE API (`validation.py::escape_lucene`) |
| SQL parameterization | All SQLite queries use parameterized `?` placeholders, never string concatenation (`tracker.py`) |
| LIKE escaping | SQL LIKE patterns escape `%`, `_`, and `\` via `escape_like()` with `ESCAPE '\'` clause (`tracker.py`) |
| Enum validation | `organize_by` and `export_format` validated against fixed allowlists (`validation.py`) |

---

### MCP06:2025 -- Intent Flow Subversion

> **Risk:** Malicious instructions embedded in context hijack the agent away from the user's original goal.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| Tool responses are data only | All tools return JSON data (experiment metadata, file lists, download results). Never instructions or commands |
| No instruction injection surface | ENCODE API responses are structured JSON, not free-text instructions. Tool outputs are serialized via `json.dumps`, not rendered as prompts |
| Metadata size limits | Raw experiment metadata capped at 512 KB to prevent payload inflation (`tracker.py`) |
| Result pagination | Search results capped at 1000 items to prevent context flooding (`validation.py::clamp_limit`) |

---

### MCP07:2025 -- Insufficient Authentication & Authorization

> **Risk:** MCP servers fail to properly verify identities or enforce access controls.

**Our status: MITIGATED (scope-appropriate)**

| Control | Implementation |
|---------|----------------|
| stdio transport only | Server uses stdin/stdout (no HTTP endpoint, no network listener). Only the parent process (Claude) can communicate with it |
| No multi-user scenario | Single-user local server. No shared access, no user accounts |
| ENCODE API auth when needed | ENCODE credentials are securely stored and sent only to `encodeproject.org` over HTTPS. Auth headers stripped on redirects |
| OS-level access control | Credential storage uses OS keyring permissions. Fallback salt file has `0o600` permissions |

---

### MCP08:2025 -- Lack of Audit and Telemetry

> **Risk:** Limited telemetry impedes investigation and incident response.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| Structured logging | All modules use `logging.getLogger(__name__)` for structured, per-module logging |
| No root logger pollution | Removed `logging.basicConfig()` to let the host application control log levels |
| Provenance tracking | Every derived file logged with source accessions, tool used, parameters, and timestamp (`tracker.py`) |
| Experiment tracking | All tracked experiments stored with full metadata, timestamps, and notes (`tracker.py`) |
| Download results | Every download returns structured results with success/failure, file size, and MD5 status |

---

### MCP09:2025 -- Shadow MCP Servers

> **Risk:** Unapproved MCP server instances operate outside security governance.

**Our status: NOT APPLICABLE**

This risk addresses organizational deployment governance. The ENCODE MCP server is a single-purpose, open-source tool that:

- Runs locally on the user's machine
- Uses stdio transport (no network listener)
- Connects only to `encodeproject.org`
- Has no mechanism to spawn child servers or proxy to other MCP servers

---

### MCP10:2025 -- Context Injection & Over-Sharing

> **Risk:** Sensitive information from one task may leak to another when context windows are shared or persistent.

**Our status: MITIGATED**

| Control | Implementation |
|---------|----------------|
| No cross-session state in context | Tool results contain only ENCODE data (public genomics metadata). No user PII in responses |
| Credentials never in tool output | Credential management tool returns only status messages ("stored", "configured", "cleared"), never the actual keys |
| No context persistence | Each tool call is independent. No conversation history stored by the server |
| Scoped tracker | Local SQLite tracker stores only ENCODE experiment metadata, not user conversations or credentials |

---

## MCP Specification Best Practices

### SSRF Prevention

The MCP specification identifies SSRF as a critical risk for servers that make outbound HTTP requests.

| MCP Spec Requirement | Our Implementation |
|---------------------|-------------------|
| Enforce HTTPS | All ENCODE API calls use `https://www.encodeproject.org` only. Download URL validator rejects non-HTTPS (`validation.py::validate_download_url`) |
| Validate redirect targets | Downloads use `follow_redirects=False` with manual redirect handling. Redirect URLs are validated before following (`downloader.py::_stream_download`) |
| Restrict outbound hosts | Download URLs allowlisted to `www.encodeproject.org`, `encodeproject.org`, and `encode-public.s3.amazonaws.com` (`validation.py::ALLOWED_DOWNLOAD_HOSTS`) |
| Block absolute URLs from API | API reference paths validated to ensure they are relative paths, not absolute URLs (`validation.py::validate_encode_path`) |
| Strip auth on redirects | Auth headers removed when following redirects to S3/CDN (`downloader.py`) |

### Transport Security

| MCP Spec Requirement | Our Implementation |
|---------------------|-------------------|
| Use stdio transport | Server uses `mcp.run()` which defaults to stdio. No HTTP endpoint exposed |
| No network listener | Server is only accessible to its parent process (Claude Desktop, Claude Code, etc.) |
| Certificate verification | httpx enforces TLS certificate verification by default. No `verify=False` anywhere |

### Input Validation

| MCP Spec Requirement | Our Implementation |
|---------------------|-------------------|
| Validate all user input | Centralized validation module (`validation.py`) with 10 validators |
| Sanitize before use | All accessions, dates, paths, URLs, and enum values validated before reaching business logic |
| Prevent injection | SQL parameterization, Lucene escaping, LIKE pattern escaping, path sanitization |
| Limit resource consumption | Query limits capped at 1000, metadata size at 512 KB, rate limiting at 10 req/sec |

---

## Additional Security Controls

### SQL Injection Prevention

```
Control: Parameterized queries + LIKE escaping
File:    tracker.py
```

All SQLite queries use `?` parameter placeholders:
```python
cursor.execute("SELECT * FROM experiments WHERE accession = ?", (accession,))
```

LIKE queries use `escape_like()` to neutralize wildcards:
```python
pattern = f"%{escape_like(filter_value)}%"
cursor.execute("... WHERE field LIKE ? ESCAPE '\\'", (pattern,))
```

### Path Traversal Prevention

```
Control: Path sanitization + resolve-based containment
File:    downloader.py, validation.py
```

- Download directory paths are resolved to absolute paths via `Path.resolve()`
- Subdirectory names (experiment accessions, file formats) sanitized via `safe_path_component()` which replaces non-alphanumeric characters and rejects `..` and `.`
- Final file paths verified to be within the download directory via `is_relative_to()`

### Rate Limiting

```
Control: Client-side rate limiter
File:    encode_client.py
```

Enforces ENCODE's 10 requests/second policy using an async semaphore. All API calls pass through the rate limiter, including those triggered by batch operations.

### Download Integrity

```
Control: MD5 checksum verification
File:    downloader.py
```

- Every downloaded file is verified against the MD5 checksum from ENCODE metadata
- Verification is enabled by default (`verify_md5=True`)
- Failed verification is reported in the download results
- Concurrent downloads limited to 3 to prevent resource exhaustion

### Concurrency Safety

```
Control: asyncio.Lock + threading.Lock
File:    main.py, tracker.py
```

- `asyncio.Lock` (`_client_lock`) prevents race conditions during credential updates in the MCP server
- `threading.Lock` in `ExperimentTracker` protects SQLite writes from concurrent access
- SQLite connection uses `check_same_thread=False` with WAL mode for safe concurrent reads

---

## Security Architecture Summary

```
User (Claude) <--stdio--> MCP Server <--HTTPS--> encodeproject.org
                               |
                               |---> ~/.encode_connector/tracker.db  (local SQLite)
                               |---> ~/.encode_connector/.salt       (PBKDF2 salt, 0600)
                               |---> OS Keyring                      (encrypted credentials)
                               |---> User-specified download dir     (data files)
```

**Attack surface:**

| Surface | Protection |
|---------|-----------|
| User input (tool parameters) | Validated by `validation.py` before processing |
| ENCODE API responses | Paths validated, URLs restricted, metadata size-limited |
| Download redirects | Auth headers stripped, redirect URLs validated |
| Local database | SQL parameterized, LIKE escaped, thread-safe |
| Credentials | OS keyring + PBKDF2/Fernet fallback, never logged |
| File system | Path traversal prevented, downloads contained to user dir |

**What this server does NOT do:**

- Execute shell commands or arbitrary code
- Listen on any network port
- Store credentials in plaintext
- Send data to any host except `encodeproject.org`
- Log sensitive information
- Modify or delete user files
- Access system files or environment variables (beyond `USER`/`USERNAME` for key derivation)

---

## Test Coverage

159 tests covering all security controls:

| Test File | Tests | Coverage Area |
|-----------|------:|---------------|
| `test_validation.py` | 30 | Accession format, date format, path traversal, SSRF, URL validation, SQL escaping, Lucene escaping, limit clamping, enum validation |
| `test_auth.py` | 8 | PBKDF2 key derivation, credential encryption, keyring integration |
| `test_downloader.py` | 9 | Path resolution, organize_by validation, path traversal prevention |
| `test_tracker.py` | 24 | SQL operations, LIKE escaping, metadata size limits, compatibility analysis |
| `test_client.py` | 8 | Input validation, limit clamping, client lifecycle |
| `test_server.py` | 65 | Tool registration, input validation at tool boundary |
| `test_models.py` | 15 | Data model parsing, safe defaults |

Run all tests:
```bash
pytest tests/ -v
```

---

## References

- [OWASP MCP Top 10 (2025)](https://owasp.org/www-project-mcp-top-10/) -- Industry standard for MCP security risks
- [MCP Specification Security Best Practices](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices) -- Official MCP security guidance
- [OWASP Cheat Sheet: Securely Using Third-Party MCP Servers](https://genai.owasp.org/resource/cheatsheet-a-practical-guide-for-securely-using-third-party-mcp-servers-1-0/)
- [Microsoft MCP Azure Security Guide](https://microsoft.github.io/mcp-azure-security-guide/) -- Microsoft's guidance on OWASP MCP Top 10
- [MCP Security: Prompt Injection Prevention](https://developer.microsoft.com/blog/protecting-against-indirect-injection-attacks-mcp) -- Microsoft Developer Blog
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)
- [OAuth 2.0 Security Best Practices (RFC 9700)](https://datatracker.ietf.org/doc/html/rfc9700)
