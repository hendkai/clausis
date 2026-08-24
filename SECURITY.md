# Security policy

Clausis Core is pre-release software and is not supported for protecting
valuable or sensitive systems. Do not enable real action execution outside an
isolated Debian test machine.

## Reporting a vulnerability

Report privately through GitHub's **Private Vulnerability Reporting** on
[github.com/hendkai/clausis](https://github.com/hendkai/clausis):
**Security → Report a vulnerability**. Reports reach the maintainers directly
and are not public. Do not include real PINs, cloud tokens, voice recordings
or personal data in a report.

The coordinated disclosure process is:

1. Acknowledge receipt within two business days.
2. Assess affected versions, exploitability and severity.
3. Develop and regression-test a fix separately from feature work.
4. Publish a signed update and advisory with credits when desired.
5. Reassess CRA reporting if commercial distribution or stewardship applies.

See `docs/security/THREAT_MODEL.md` for supported security properties and known
limitations.
