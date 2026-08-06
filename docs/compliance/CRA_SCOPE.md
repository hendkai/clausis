# CRA scope assessment

Assessment date: 2026-08-06. Status: **unclear for future distribution; not a
claim of conformity and not legal advice**.

## Current prototype

VoiceOS Core is software with network-capable components, but the stated model
is free open-source publication without monetisation, paid support or commercial
service. On that assumption, it is probably outside the CRA manufacturer scope.
The European Commission states that free and open-source software falls within
the CRA when supplied for distribution or use in the course of commercial
activity. A legal entity providing sustained support for software intended for
commercial activities may instead become an open-source software steward.

Official source: <https://digital-strategy.ec.europa.eu/en/policies/cra-open-source>

## Triggered reassessment

Reassess before any of the following:

- paid support, subscription, dual licensing, hosted services or bundled cloud;
- publication by a legal entity providing sustained stewardship;
- commercial hardware distribution or OEM image agreements;
- a release after 11 December 2027 into the EU market;
- a substantial modification of security-relevant functionality.

If commercialised, the preliminary technical classification is likely a
standard product with digital elements, but this is non-binding and requires a
formal classification against Regulation (EU) 2024/2847 and Implementing
Regulation (EU) 2025/2392.

## Voluntary security evidence already started

- Typed least-privilege action boundary and threat model.
- CycloneDX SBOM for the repository component.
- Signed-update and rollback design, not yet implemented.
- Coordinated vulnerability disclosure draft and release blocker.
- Support/EOL draft and per-release license inventory.

## Current gaps

- No accountable manufacturer/steward or security contact is named.
- No released product, support period, signed repository or incident team.
- No production SBOM for a complete ISO and no penetration test.
- ENISA/BSI incident reporting ownership is not assigned.

Official references checked 2026-08-06:

- <https://eur-lex.europa.eu/eli/reg/2024/2847/oj>
- <https://digital-strategy.ec.europa.eu/en/library/cyber-resilience-act-implementation-frequently-asked-questions>
- <https://www.bsi.bund.de/EN/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/Technische-Richtlinien/TR-nach-Thema-sortiert/tr03183/tr-03183.html>

