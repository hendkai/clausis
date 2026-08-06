"""Compatibility build entry point for minimal Debian/installer environments."""

from setuptools import find_packages, setup


setup(
    name="voiceos-core",
    version="0.1.0",
    description="Security-first voice control core for Debian and Hermes Agent",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    package_dir={"": "src"},
    packages=find_packages("src"),
    python_requires=">=3.9",
    license="GPL-3.0-or-later",
    extras_require={
        "dbus": ["dbus-next>=0.2.3"],
        "voice": ["faster-whisper>=1.0", "sounddevice>=0.4", "numpy>=1.24"],
        "test": ["pytest>=7", "coverage>=7"],
    },
    entry_points={
        "console_scripts": [
            "voiceosctl=voiceos.cli:main",
            "voiceos-healthcheck=voiceos.healthcheck:main",
            "voiceos-broker=voiceos.services:broker_main",
            "voiceos-trusted-confirm=voiceos.services:confirm_main",
            "voiceos-runtime=voiceos.runtime:main",
            "voiceos-assistant=voiceos.assistant:main",
        ]
    },
)
