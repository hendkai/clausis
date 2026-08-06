from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LiveImageConfigurationTests(unittest.TestCase):
    def test_graphical_live_autologin_dependencies_are_present(self) -> None:
        package_list = (
            ROOT
            / "packaging/live-build/config/package-lists/clausis.list.chroot"
        ).read_text(encoding="utf-8").splitlines()

        self.assertIn("gdm3", package_list)
        self.assertIn("live-config-systemd", package_list)
        self.assertIn("user-setup", package_list)

    def test_live_user_is_selected_on_the_kernel_command_line(self) -> None:
        config = (ROOT / "packaging/live-build/auto/config").read_text(
            encoding="utf-8"
        )
        self.assertIn("boot=live", config)
        self.assertIn("username=clausis", config)

    def test_debian_13_live_password_compatibility_hook_is_installed(self) -> None:
        hook = (
            ROOT
            / "packaging/live-build/config/includes.chroot/usr/lib/live/config"
            / "0035-clausis-live-user"
        ).read_text(encoding="utf-8")

        self.assertIn("usermod --password", hook)
        self.assertIn("usermod --append --groups clausis-control", hook)
        self.assertIn("chage --expiredate -1", hook)
        self.assertNotIn("clausis:live", hook)

    def test_service_group_does_not_collide_with_live_username(self) -> None:
        postinst = (ROOT / "debian/clausis-core.postinst").read_text(encoding="utf-8")

        self.assertIn("group clausis-control", postinst)
        self.assertNotIn("group clausis >/dev/null", postinst)
