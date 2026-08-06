# Biometric and voice privacy assessment — draft

Status: release blocker; requires a responsible controller and qualified
privacy review. This document is not legal advice.

## Proposed processing

Wake-word and command audio are processed locally by default and discarded
after transcription. Voice-login would derive an encrypted speaker template;
raw enrollment audio is not retained. Cloud transmission is off until the user
chooses a provider and gives explicit, provider-specific consent.

## Necessity and alternatives

The speaker template is not necessary for the core voice desktop. It is an
optional home-use convenience feature. Password, FIDO2, keyboard, Orca and
recovery access must remain available, so refusal or withdrawal does not block
the operating system.

## Required controls before implementation

- Local-only template processing, TPM-bound encryption and explicit enrollment.
- Separate consent for voice template and every cloud provider/data flow.
- On-device view, reset and irreversible deletion of template and consent.
- No emotion recognition, biometric categorisation or remote identification.
- Retention schedule, controller contact, lawful-basis analysis and data-subject
  request process.
- Bias/error testing across the intended user population, including speech
  impairments and accents.
- Incident response for template disclosure and a documented fallback.

## Open risks

Voice cloning and replay cannot be reliably excluded by the current prototype.
No speaker-recognition model has been selected or licensed. The feature must not
be marketed as strong authentication or theft protection.

