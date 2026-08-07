# Third-party notices

## Hermes Agent

The 0.2.0 image installs Hermes Agent 0.20.0 from pinned upstream commit
`0957277f2f468bac22bbfcfa7c43029858c9597e`. Its source checkout, locked Python
environment, copyright notice and complete MIT license are included in the
image. The license is also copied to `/usr/share/doc/hermes-agent/LICENSE`.

> MIT License — Copyright (c) 2025 Nous Research

Upstream: <https://github.com/NousResearch/hermes-agent>

License: <https://github.com/NousResearch/hermes-agent/blob/main/LICENSE>

## Local speech stack in the 0.2.0 ISO

The ISO build installs `faster-whisper` 1.2.1 and `python-sounddevice` 0.5.5.
Both projects are MIT-licensed. Their installed Python distributions retain
their complete license metadata in `/opt/clausis/lib/python*/site-packages/`.

- faster-whisper: Copyright (c) 2023 SYSTRAN. Source and license:
  <https://github.com/SYSTRAN/faster-whisper>
- python-sounddevice: Copyright (c) Matthias Geier. Source and license:
  <https://github.com/spatialaudio/python-sounddevice>

The ISO also contains the `Systran/faster-whisper-base` CTranslate2 model,
converted from `openai/whisper-base`. The model repository identifies the
artifact as MIT-licensed. OpenAI states that the original Whisper code and
weights are MIT-licensed (Copyright (c) 2022 OpenAI).

- Converted model and model card:
  <https://huggingface.co/Systran/faster-whisper-base>
- Original Whisper source and license: <https://github.com/openai/whisper>

The model is used only for local transcription. Clausis does not retain raw
recordings after an utterance is processed. Debian packages in the image keep
their machine-readable copyright files under `/usr/share/doc/*/copyright`.
Future release automation must generate an artifact-level SBOM and complete
license manifest from the final image; the repository SBOM is not a substitute.
