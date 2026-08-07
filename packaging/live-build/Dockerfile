FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools syslinux-utils isolinux \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools ca-certificates rsync \
    build-essential devscripts debhelper dh-python pybuild-plugin-pyproject \
    python3-all python3-setuptools python3-build && \
    rm -rf /var/lib/apt/lists/*

COPY build-in-container /usr/local/bin/build-clausis-iso
RUN chmod 0755 /usr/local/bin/build-clausis-iso

# Build the exact Debian Stable Calamares source with a minimal GPL-compatible
# patch that exports only non-secret in-memory partition choices. The resulting
# higher-versioned package is injected into the live image; build dependencies
# remain in this builder layer and never enter Clausis.
COPY debian-src.sources /etc/apt/sources.list.d/clausis-src.sources
COPY patches/calamares/0001-export-selected-device-metadata.patch /tmp/calamares.patch
RUN apt-get update && \
    apt-get build-dep -y calamares && \
    mkdir -p /usr/src/clausis-calamares /opt/clausis-calamares-debs && \
    cd /usr/src/clausis-calamares && \
    apt-get source calamares=3.3.14-1 && \
    cd calamares-3.3.14 && \
    patch -p1 < /tmp/calamares.patch && \
    DEBEMAIL=maintainers@example.invalid DEBFULLNAME='Clausis contributors' \
        dch --local +clausis1 --distribution trixie \
        'Export non-secret selected-device metadata for the Clausis pre-write guard.' && \
    DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -us -uc -b && \
    cp ../calamares_*_amd64.deb /opt/clausis-calamares-debs/ && \
    rm -rf /var/lib/apt/lists/* /usr/src/clausis-calamares
ENTRYPOINT ["/usr/local/bin/build-clausis-iso"]
