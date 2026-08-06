FROM debian:stable-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    live-build debootstrap xorriso squashfs-tools syslinux-utils isolinux \
    grub-pc-bin grub-efi-amd64-bin mtools dosfstools ca-certificates rsync \
    build-essential devscripts debhelper dh-python pybuild-plugin-pyproject \
    python3-all python3-setuptools python3-build && \
    rm -rf /var/lib/apt/lists/*

COPY build-in-container /usr/local/bin/build-voiceos-iso
RUN chmod 0755 /usr/local/bin/build-voiceos-iso
ENTRYPOINT ["/usr/local/bin/build-voiceos-iso"]
