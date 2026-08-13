from __future__ import annotations

import struct
import hashlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def png_metadata(path: Path) -> tuple[int, int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise AssertionError(f"{path} is not a PNG image")
    width, height, _depth, colour_type = struct.unpack(">IIBB", data[16:26])
    return width, height, colour_type


class BrandingTests(unittest.TestCase):
    def test_source_logo_is_transparent_png(self) -> None:
        path = ROOT / "assets/branding/clausis-logo.png"
        self.assertEqual(png_metadata(path), (1254, 1254, 6))

    def test_grub_splash_has_expected_boot_dimensions(self) -> None:
        path = ROOT / "packaging/live-build/config/bootloaders/grub-pc/splash.png"
        self.assertEqual(png_metadata(path), (800, 600, 2))

    def test_syslinux_splash_has_expected_boot_dimensions(self) -> None:
        path = ROOT / "packaging/live-build/config/bootloaders/syslinux_common/splash.png"
        self.assertEqual(png_metadata(path), (640, 480, 2))

    def test_approved_version_neutral_boot_splashes_are_unchanged(self) -> None:
        """Prevent stale release badges from silently returning to boot media."""

        expected = {
            "grub-pc/splash.png": "1b1ba72fb19638308ccb01aaef2f0cd09db429357a2d1a8a33667b9dc8e8f730",
            "syslinux_common/splash.png": "eaeaca3fdf5b712d650efe14db4e5118c885c21b6eb129a3122d6126b9a53c27",
        }
        root = ROOT / "packaging/live-build/config/bootloaders"
        for relative, digest in expected.items():
            with self.subTest(asset=relative):
                self.assertEqual(
                    hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest
                )

    def test_gnome_theme_uses_clausis_branding_and_accessible_defaults(self) -> None:
        image_root = ROOT / "packaging/live-build/config/includes.chroot"
        wallpaper_source = (
            image_root / "usr/share/backgrounds/clausis/clausis-wallpaper.svg"
        )
        wallpaper = image_root / "usr/share/backgrounds/clausis/clausis-wallpaper.png"
        logo = image_root / "usr/share/pixmaps/clausis-logo.png"
        dconf = (image_root / "etc/dconf/db/local.d/00-clausis").read_text(
            encoding="utf-8"
        )
        gdm = (image_root / "etc/dconf/db/gdm.d/00-clausis").read_text(
            encoding="utf-8"
        )
        packages = (
            ROOT / "packaging/live-build/config/package-lists/clausis.list.chroot"
        ).read_text(encoding="utf-8")

        self.assertTrue(wallpaper_source.is_file())
        self.assertEqual(png_metadata(wallpaper), (2560, 1440, 2))
        self.assertEqual(png_metadata(logo), (1254, 1254, 6))
        self.assertIn("color-scheme='prefer-dark'", dconf)
        self.assertIn("accent-color='purple'", dconf)
        self.assertIn("Atkinson Hyperlegible 11", dconf)
        self.assertIn("enable-animations=false", dconf)
        self.assertIn("toolkit-accessibility=true", dconf)
        self.assertIn("always-show-universal-access-status=true", dconf)
        self.assertIn("clausis-wallpaper.png", dconf)
        self.assertIn("fonts-atkinson-hyperlegible", packages)
        self.assertIn("logo='/usr/share/pixmaps/clausis-logo.png'", gdm)

        for launcher_name in (
            "clausis-assistant.desktop",
            "clausis-setup.desktop",
        ):
            launcher = (
                image_root / "usr/share/applications" / launcher_name
            ).read_text(encoding="utf-8")
            self.assertIn("Icon=clausis-logo", launcher)

        hermes_launcher = (
            image_root / "usr/share/applications/clausis-hermes-chat.desktop"
        ).read_text(encoding="utf-8")
        self.assertIn("Icon=hermes-agent", hermes_launcher)
