# Support and lifecycle policy — draft

No end-user release exists yet. Version 0.3.1 is a development prototype and
receives no production security guarantee.

Before a stable release, maintainers must publish an exact security-support end
date, supported Debian base, hardware profile, update channel and migration/EOL
path. The planning default is five years of free security updates for a stable
image, subject to confirmation of maintainer capacity and upstream Debian
support. This planning default is not currently a contractual promise.

Security fixes are separated from feature releases. Proposed internal targets:

- critical actively exploited issue: triage immediately, mitigation target 24 h;
- high severity: fix target 72 h when feasible;
- medium/low: next scheduled security update.
