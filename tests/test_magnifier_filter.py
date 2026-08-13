import subprocess
import unittest

from clausis.magnifier_filter import main, set_filter


class MagnifierFilterTests(unittest.TestCase):
    def test_sets_all_three_brightness_channels_with_fixed_argv(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, stdout="0.0\n", stderr="")

        set_filter("brightness", "-0.30", runner=runner)
        self.assertEqual([call[0][3] for call in calls[:3]], [
            "brightness-red", "brightness-green", "brightness-blue"
        ])
        self.assertEqual([call[0][3] for call in calls[3:]], [
            "brightness-red", "brightness-green", "brightness-blue"
        ])
        self.assertTrue(all(call[0][-1] == "-0.30" for call in calls[3:]))
        self.assertTrue(all(call[1]["check"] for call in calls))

    def test_sets_all_three_contrast_channels(self):
        calls = []

        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="0.0\n", stderr="")

        set_filter("contrast", "0.75", runner=runner)
        self.assertEqual([argv[3] for argv in calls[3:]], [
            "contrast-red", "contrast-green", "contrast-blue"
        ])

    def test_rejects_noncanonical_kind_value_and_range(self):
        for kind, value in (
            ("saturation", "0.20"),
            ("brightness", "0.2"),
            ("brightness", "+0.20"),
            ("brightness", "0.76"),
            ("contrast", "nan"),
        ):
            with self.subTest(kind=kind, value=value), self.assertRaises(ValueError):
                set_filter(kind, value)

    def test_rolls_back_changed_channels_after_partial_failure(self):
        calls = []
        set_count = 0

        def runner(argv, **kwargs):
            nonlocal set_count
            calls.append((argv, kwargs))
            if argv[1] == "get":
                return subprocess.CompletedProcess(argv, 0, stdout="0.1\n", stderr="")
            set_count += 1
            if set_count == 2:
                raise subprocess.CalledProcessError(1, argv)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

        with self.assertRaises(subprocess.CalledProcessError):
            set_filter("brightness", "0.20", runner=runner)
        rollback = calls[-1]
        self.assertEqual(rollback[0][-1], "0.1")
        self.assertFalse(rollback[1]["check"])

    def test_main_rejects_wrong_arity_without_execution(self):
        self.assertEqual(main([]), 2)
        self.assertEqual(main(["brightness"]), 2)
        self.assertEqual(main(["brightness", "0.20", "extra"]), 2)
