# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.2.x | ✅ |
| < 0.2 | ❌ |

## Reporting a vulnerability

If you discover a security issue, please **do not** open a public GitHub issue.

Instead, report it privately to the repository owner via GitHub Security Advisories:

<https://github.com/suribe06/cursor-agent-beacon/security/advisories/new>

Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You should receive a response within a reasonable timeframe. We will coordinate disclosure and a fix before publishing details publicly.

## Scope notes

This project runs locally on the developer machine:

- Cursor hooks invoke a local Python handler
- The bridge binds to `127.0.0.1` by default
- Serial output targets a local USB device

Report issues such as unintended network exposure, path traversal in file sinks, or unsafe deserialization of hook payloads.
