"""Compatibility build entry point for minimal Debian/installer environments."""

from setuptools import find_packages, setup


setup(
    name="clausis-core",
    version="0.2.1",
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
            "clausisctl=clausis.cli:main",
            "clausis-healthcheck=clausis.healthcheck:main",
            "clausis-broker=clausis.services:broker_main",
            "clausis-trusted-confirm=clausis.services:confirm_main",
            "clausis-runtime=clausis.runtime:main",
            "clausis-assistant=clausis.assistant:main",
            "clausis-setup=clausis.setup_app:main",
            "clausis-finalize-hermes-install=clausis.finalize_install:main",
        ]
    },
)
