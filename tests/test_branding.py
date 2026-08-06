from __future__ import annotations

import struct
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
