"""Structural checks for the privileged helper and the GNOME Shell bridge.

Neither component can be exercised on a build host without Polkit or a running
GNOME Shell, so these tests assert the wiring instead: the Polkit action must
point at the helper this repository ships, the Debian package must install it,
and the extension must export exactly the interface the Python client calls.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unittest

from clausis.gnome_adapter import CLIPBOARD_READ_METHOD, SHELL_ACTIONS, DbusGnomeShell
from clausis.privileged import HELPER_PATH


ROOT = Path(__file__).resolve().parents[1]
EXTENSION_UUID = "clausis@clausis.local"
EXTENSION_DIR = ROOT / "packaging/gnome-shell" / EXTENSION_UUID


class PrivilegedHelperPackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.helper = ROOT / "packaging/libexec/clausis-system-action"

    def test_helper_exists_and_is_executable(self) -> None:
        self.assertTrue(self.helper.is_file())
        self.assertTrue(self.helper.stat().st_mode & 0o111)

    def test_helper_is_not_group_or_world_writable(self) -> None:
        self.assertEqual(self.helper.stat().st_mode & 0o022, 0)

    def test_polkit_action_points_at_the_shipped_helper(self) -> None:
        policy = (ROOT / "packaging/polkit/org.clausis.policy").read_text(encoding="utf-8")
        self.assertIn(f">{HELPER_PATH}<", policy)
        self.assertIn("auth_admin_keep", policy)

    def test_debian_package_installs_the_helper(self) -> None:
        install = (ROOT / "debian/clausis-core.install").read_text(encoding="utf-8")
        self.assertIn("packaging/libexec/clausis-system-action usr/libexec/", install)
        self.assertTrue(HELPER_PATH.startswith("/usr/libexec/"))

    def test_helper_delegates_to_the_tested_module(self) -> None:
        source = self.helper.read_text(encoding="utf-8")
        self.assertTrue(source.startswith("#!/usr/bin/python3"))
        self.assertIn("from clausis.privileged import helper_main", source)
        # The shipped script must stay a shim: all decisions live in the module
        # that the unit tests cover.
        self.assertNotIn("subprocess", source)

    def test_postinst_keeps_the_capability_key_root_only(self) -> None:
        postinst = (ROOT / "debian/clausis-core.postinst").read_text(encoding="utf-8")
        self.assertIn("chmod 0600 /etc/clausis/capability.key", postinst)
        self.assertIn("chown root:root /etc/clausis/capability.key", postinst)
        self.assertNotIn("chown root:clausis-control /etc/clausis/capability.key", postinst)


class ShellExtensionPackagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metadata = json.loads((EXTENSION_DIR / "metadata.json").read_text(encoding="utf-8"))
        self.source = (EXTENSION_DIR / "extension.js").read_text(encoding="utf-8")

    def test_metadata_uuid_matches_the_directory(self) -> None:
        self.assertEqual(self.metadata["uuid"], EXTENSION_UUID)
        self.assertTrue(self.metadata["shell-version"])

    def test_extension_exports_the_interface_the_client_calls(self) -> None:
        self.assertIn(f"'{DbusGnomeShell.BUS_NAME}'", self.source)
        self.assertIn(f"'{DbusGnomeShell.PATH}'", self.source)
        self.assertIn(f'<interface name="{DbusGnomeShell.INTERFACE}">', self.source)

    def test_every_declared_method_is_implemented(self) -> None:
        declared = set(re.findall(r'<method name="(\w+)">', self.source))
        self.assertIn("ShowOverview", declared)
        for name in declared:
            # Either the synchronous form or the GJS async convention.
            self.assertRegex(
                self.source,
                rf"\n    {name}\(\) \{{|\n    {name}Async\(params, invocation\) \{{",
            )

    def test_every_mapped_shell_action_exists_in_the_extension(self) -> None:
        # A Clausis action that names a method the extension does not export
        # would fail only in a live GNOME session, so it is checked here.
        declared = set(re.findall(r'<method name="(\w+)">', self.source))
        for action, (method, _spoken) in SHELL_ACTIONS.items():
            with self.subTest(action=action):
                self.assertIn(method, declared)

    def test_clipboard_read_method_exists_and_is_read_only(self) -> None:
        declared = set(re.findall(r'<method name="(\w+)">', self.source))
        self.assertIn(CLIPBOARD_READ_METHOD, declared)
        # Writing the clipboard would need an input argument, which this
        # interface must not have; the AT-SPI copy action covers that direction.
        self.assertNotIn("set_text", self.source)

    def test_bridge_exposes_no_evaluation_or_input_simulation(self) -> None:
        for forbidden in ("eval(", "Function(", "Clutter.Event", "fakeKey", "global.stage"):
            self.assertNotIn(forbidden, self.source)

    def test_all_methods_are_parameterless(self) -> None:
        # An argument would let a compromised session process name an arbitrary
        # shell object; the bridge only offers fixed surfaces.
        self.assertNotIn('direction="in"', self.source)

    def test_debian_package_installs_the_extension(self) -> None:
        install = (ROOT / "debian/clausis-core.install").read_text(encoding="utf-8")
        for name in ("metadata.json", "extension.js"):
            self.assertIn(
                f"packaging/gnome-shell/{EXTENSION_UUID}/{name} "
                f"usr/share/gnome-shell/extensions/{EXTENSION_UUID}/",
                install,
            )

    def test_live_image_enables_the_extension(self) -> None:
        dconf = (
            ROOT / "packaging/live-build/config/includes.chroot/etc/dconf/db/local.d/00-clausis"
        ).read_text(encoding="utf-8")
        self.assertIn(f"enabled-extensions=['{EXTENSION_UUID}']", dconf)
        self.assertIn("disable-user-extensions=false", dconf)


if __name__ == "__main__":
    unittest.main()
