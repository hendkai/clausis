# Clausis branding

`clausis-logo.png` is the primary Clausis symbol. It combines a rounded `C`,
a speech waveform and two audio-pulse arcs so that the mark remains recognisable
in the low-resolution boot menu.

The emblem was generated specifically for Clausis with OpenAI image generation
on 2026-08-06 and then reviewed, chroma-keyed and composed into the boot splash
images by Codex. It does not reuse the Debian helmet, Debian swirl, Tux or a
third-party logo. The source emblem and the derived boot images are distributed
under the repository's GPL-3.0-or-later license.

Derived boot assets:

- `packaging/live-build/config/bootloaders/grub-pc/splash.png` (800×600)
- `packaging/live-build/config/bootloaders/syslinux_common/splash.png` (640×480)

The GNOME identity uses the same mark rather than a separate desktop logo. Its
palette is a deep listening field (`#070a17`, `#17234a`), orientation cyan
(`#20d8f2`), active-speech violet (`#7937e8`) and high-contrast ice text. The
desktop wallpaper keeps the left side quiet for windows and icons while the
emblem and three concentric listening rings occupy the right side. GNOME uses
the supported dark color preference, purple accent, reduced animation and
Atkinson Hyperlegible type rather than a forked GTK theme.

Derived desktop assets:

- `packaging/live-build/config/includes.chroot/usr/share/backgrounds/clausis/clausis-wallpaper.png`
  (2560×1440)
- the matching SVG composition source beside the PNG;
- `packaging/live-build/config/includes.chroot/usr/share/pixmaps/clausis-logo.png`
  for GNOME applications and GDM.
