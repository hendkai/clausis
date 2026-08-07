# Third-party notices

## Modified Calamares installer

The development image builds Debian's Calamares 3.3.14-1 source with the public
Clausis patches `0001-export-selected-device-metadata.patch` and
`0002-install-clausis-recovery-key.patch`, producing package version
`3.3.14-1+clausis11`. The patches add non-secret selected-device metadata for
the pre-write guard and internally enroll the ephemeral Clausis recovery key in
the installed LUKS volume. Calamares is GPL-3.0-or-later.
The exact source package, Debian packaging, Clausis patch and complete build
recipe are identified by `packaging/live-build/Dockerfile`; installed Debian
copyright and license files remain in the image.

- Upstream: <https://github.com/calamares/calamares>
- Debian source package: <https://packages.debian.org/source/trixie/calamares>
- Clausis patch: `packaging/live-build/patches/calamares/0001-export-selected-device-metadata.patch`
- Clausis recovery patch: `packaging/live-build/patches/calamares/0002-install-clausis-recovery-key.patch`

## Hermes Agent

The 0.4.1 image installs Hermes Agent 0.20.0 from pinned upstream commit
`0957277f2f468bac22bbfcfa7c43029858c9597e`. Its source checkout, locked Python
environment, copyright notice and complete MIT license are included in the
image. The license is also copied to `/usr/share/doc/hermes-agent/LICENSE`.
During an online operating-system installation, Clausis may replace the active
launcher with the latest official stable Hermes release. That release remains
MIT-licensed, is installed from its exact Git tag and frozen `uv.lock`, and
retains its `LICENSE` in the installed source directory. The selected tag and
commit are recorded in `/var/lib/clausis/hermes-install.json`.

> MIT License — Copyright (c) 2025 Nous Research

Upstream: <https://github.com/NousResearch/hermes-agent>

License: <https://github.com/NousResearch/hermes-agent/blob/main/LICENSE>

## Local speech stack in the 0.4.1 ISO

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

## Optional GPT Live transport in the 0.4.1 ISO

The ISO installs `websocket-client` 1.9.0 for the voluntary OpenAI Realtime
WebSocket connection. The project is Apache-2.0 licensed and its installed
distribution retains the license metadata in `/opt/clausis/lib/python*/site-packages/`.

- websocket-client source and license:
  <https://github.com/websocket-client/websocket-client>

`gpt-realtime-2.1` is a remotely accessed OpenAI service, not a model bundled or
redistributed in the ISO. Clausis includes no OpenAI API key or proprietary
model weight.

## GNOME legibility font in the 0.4.1 ISO

The ISO installs Debian's `fonts-atkinson-hyperlegible` package. The font is
Copyright 2020 Braille Institute of America, Inc. and licensed under the SIL
Open Font License 1.1. Debian retains its complete machine-readable copyright
and license at `/usr/share/doc/fonts-atkinson-hyperlegible/copyright`.

- Upstream source: <https://github.com/googlefonts/atkinson-hyperlegible>

## GNOME AT-SPI Python binding in the 0.4.1 ISO

The ISO installs Debian's `python3-pyatspi` 2.46.1-1 package for bounded
semantic access to the GNOME accessibility tree. The main upstream code is
LGPL-2.0 licensed. Separately identified examples and tests use the additional
licenses listed in Debian's complete record at
`/usr/share/doc/python3-pyatspi/copyright`.

- Upstream source: <https://gitlab.gnome.org/GNOME/pyatspi2>
