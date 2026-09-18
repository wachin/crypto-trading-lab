# ADR-0004: Credential Storage

## Status
Accepted

## Context
User credentials (exchange API keys) must be stored securely:
* Must persist between sessions
* Must not be readable by other applications
* Should follow platform security standards

## Decision
We use the **system keyring** (`python3-keyring`). On Debian this uses `libsecret`.

## Consequences

### Positive
* Encrypted storage via OS
* Follows platform conventions
* Easy to rotate/delete credentials

### Negative
* Requires OS-level encryption support
* Slightly more complex to test on CI

### Alternatives Considered
* **Encrypted local file**: Key management adds complexity
* **Environment variables**: Not suitable for persistent storage
