# Privacy Policy

**ENCODE Toolkit**
*Last updated: March 2026*

## Overview

The ENCODE Toolkit is a local software tool that runs entirely on your machine. It is designed with privacy as a core principle.

## Data Collection

**We collect no data.** The ENCODE Toolkit:

- Has **no telemetry**
- Has **no analytics**
- Has **no tracking**
- Has **no user accounts** on our side
- Sends **no data** to the developer or any third party
- Does **not phone home** for any reason

## Network Connections

The Software makes network connections **only** to the following endpoint:

- `https://www.encodeproject.org` — the ENCODE Project REST API, operated by Stanford University

These connections are made solely to fulfill your search, metadata, and download requests. All connections use HTTPS with certificate verification enforced.

**No other external connections are made.** The Software does not contact any analytics services, advertising networks, or third-party APIs.

## Data Storage

All data created by the Software is stored **locally on your machine**:

- **Tracked experiments** — stored in a local SQLite database in your home directory (`~/.encode-toolkit/tracker.db`)
- **Downloaded files** — saved to directories you specify
- **Credentials** (if provided) — encrypted using your operating system's keyring (macOS Keychain, Linux Secret Service, Windows Credential Locker) or a local encrypted file with restricted permissions

No data is stored remotely. No data is shared with the developer or any third party.

## ENCODE API

When you search or download data, your queries are sent to the ENCODE Project API at `encodeproject.org`. The ENCODE Project is operated by Stanford University and is funded by the National Human Genome Research Institute (NHGRI). Their data use policies apply to data retrieved from their API. See: https://www.encodeproject.org/help/data-use-policy/

## Credentials

If you provide ENCODE API credentials (for accessing restricted/unreleased data), they are:

- Stored in your OS keyring (preferred) or encrypted locally with Fernet symmetric encryption
- Never transmitted to anyone other than `encodeproject.org`
- Never logged or written to plaintext files
- Clearable at any time via the `encode_manage_credentials` tool

## Children's Privacy

The Software does not knowingly collect any personal information from anyone, including children under 13.

## Changes

If this privacy policy changes, the updated policy will be included in the Software distribution. Since the Software collects no data, meaningful privacy changes are unlikely.

## Contact

For privacy questions: ammawla@ucdavis.edu

**Author:** Dr. Alex M. Mawla, PhD
