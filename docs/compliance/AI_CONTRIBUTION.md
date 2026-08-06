# AI contribution record

## Document control

| Field | Value |
|---|---|
| Product | VoiceOS Core |
| Version | 0.1.0 prototype |
| Date | 2026-08-06 |
| Responsible role | Open; must be assigned before release |
| Status | Draft, release blocked |
| Next review | 2027-02-06 or earlier on a trigger below |

## Development provenance

AI-assisted tools were used to propose, draft, transform and review the product
concept, Python implementation, tests, Debian Live ISO configuration, local
speech integration, packaging and documentation. Known tools
in this work session included OpenAI Codex/GPT-5-family assistance and Claude
Code Opus 5 for architecture review. A Claude Fable 5 review was attempted but
did not return a usable review. Exact model-side implementation details and
training data are unknown.

Automated tests were executed after implementation. No human code, security,
accessibility, privacy or legal sign-off has yet been recorded; it would be
misleading to claim that the result is production-ready or fully compliant.
The complete 60-test suite and Debian binary-package build also passed inside
an official fresh Debian Stable container. A later Opus 5 source-review attempt
did not return output and therefore is not counted as review evidence.

On 2026-08-06 Codex added the first local audio frontend, the accessible live
session welcome, a Calamares-based installation image configuration and a
containerised amd64 ISO build. The ISO includes the MIT-licensed converted
`Systran/faster-whisper-base` model and pinned speech libraries. Any ISO build
and structural boot checks are recorded separately from human hardware,
accessibility, privacy and security approval.

The completed artifact was structurally verified and booted under x86-64 QEMU
through the live root to GNOME Display Manager. This evidence is documented in
`docs/release/ISO_0.1.0_TEST_REPORT.md`; it does not establish physical audio,
USB installation, accessibility user-study or production-security fitness.

Evidence:

- `tests/` and the latest local test output;
- `docs/security/THREAT_MODEL.md`;
- `docs/release/RELEASE_GATE.md`;
- `docs/compliance/CRA_SCOPE.md`;
- `sbom.cdx.json` and `THIRD_PARTY_NOTICES.md`.

## AI functions in the product

The planned product integrates Hermes Agent for direct natural-language
interaction and may use local or user-selected cloud models. The deterministic
offline router is rule-based and is not treated as AI. The 0.1.0 ISO uses a
local Faster-Whisper base model for STT and eSpeak NG/speech-dispatcher for
synthetic speech. Wake-word and speaker-verification models remain unselected
and unbundled.

Target users are private individuals in the EU, including people relying on
accessibility functions. The present prototype does not implement medical,
employment, education, credit, law-enforcement or public-authority decisions.

## EU AI Act assessment

| Question | Current assessment |
|---|---|
| AI system remains in product | Yes, when Hermes/model integration is installed. |
| Direct interaction with people | Yes; first interaction must disclose that Hermes is AI. |
| Synthetic audio | Planned TTS; saved/exported audio marking must be assessed when a provider is selected. |
| Emotion recognition or biometric categorisation | No; prohibited by product requirements. |
| Biometric verification | Planned optional speaker verification; separate privacy/legal review required. |
| High-risk or prohibited use | Not identified for intended household accessibility use; reassess on any use expansion. |
| Visible notice | Live session implements spoken and visual notice before opening the installer; installed-system first run still requires verification. |
| Machine-readable marking | Not implemented; applicability depends on selected TTS/export behavior and current standards. |

Article 50 transparency obligations apply from 2 August 2026. The current
consolidated AI Act version available on EUR-Lex is dated 27 July 2026. This is
a technical scope assessment, not legal advice.

## Official sources checked on 2026-08-06

- Consolidated Regulation (EU) 2024/1689:
  <https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689>
- European Commission Article 50 guidelines, published 20 July 2026:
  <https://digital-strategy.ec.europa.eu/en/library/guidelines-transparency-obligations-providers-and-deployers-ai-systems>
- European Commission CRA open-source guidance:
  <https://digital-strategy.ec.europa.eu/en/policies/cra-open-source>
- European Commission CRA implementation FAQ:
  <https://digital-strategy.ec.europa.eu/en/library/cyber-resilience-act-implementation-frequently-asked-questions>

## Open actions and triggers

High priority: assign responsible reviewers; verify first-run disclosure on
hardware; complete model dependency/license inventory; complete DPIA; close every release blocker;
and obtain human security/accessibility review.

Reassess immediately on a release, model/provider/data-flow change, biometric
feature implementation, commercialisation, target-market/use expansion,
security/privacy incident or change in applicable law/guidance. Otherwise
reassess no later than the date above.

This record distinguishes voluntary development provenance from product-law
obligations. It is not a legal opinion or a guarantee of compliance.
