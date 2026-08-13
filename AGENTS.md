# Project instructions

- Treat Clausis as a Debian/VirtualBox target, not as a Windows-native application.
- For every functional change, run the relevant automated tests first.
- Before calling an installer, boot, desktop, audio, or recovery change complete,
  build the ISO and test the real flow in VirtualBox. Record missing VirtualBox
  validation explicitly as a release blocker; a host-only unit test is not a
  substitute.
- Never perform destructive installer tests against a host disk. Use a dedicated,
  disposable VirtualBox virtual disk.
