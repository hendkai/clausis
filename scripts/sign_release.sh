#!/bin/sh
# Sign the release artifacts in dist/ with the Clausis release key.
#
# Checksums alone prove nothing about origin: whoever can replace the ISO can
# replace the checksum file next to it. A detached OpenPGP signature over the
# checksum file is what lets a downloader tell a genuine image from a
# substituted one.
#
# Required environment:
#   CLAUSIS_SIGNING_KEY_ID  fingerprint or key id of the release key
# Optional:
#   CLAUSIS_SIGNING_KEY     ASCII-armoured private key to import first
#                           (for CI; prefer a hardware token interactively)
#   GNUPGHOME               keyring to use; a private temporary one is created
#                           when a key is imported
#
# This script fails closed: without a key id nothing is signed and nothing is
# published as if it were signed.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
dist_dir="${1:-$project_dir/dist}"

if [ -z "${CLAUSIS_SIGNING_KEY_ID:-}" ]; then
    echo "BLOCKED: CLAUSIS_SIGNING_KEY_ID is not set; refusing to publish unsigned artifacts" >&2
    exit 1
fi

cleanup() {
    if [ -n "${temporary_home:-}" ]; then
        rm -rf "$temporary_home"
    fi
}
temporary_home=
trap cleanup EXIT INT TERM

if [ -n "${CLAUSIS_SIGNING_KEY:-}" ]; then
    temporary_home=$(mktemp -d)
    chmod 0700 "$temporary_home"
    GNUPGHOME="$temporary_home"
    export GNUPGHOME
    printf '%s\n' "$CLAUSIS_SIGNING_KEY" | gpg --batch --quiet --import
fi

version=$("$project_dir/scripts/project_version.sh")
checksum="$dist_dir/clausis-$version-amd64.iso.sha256"

if [ ! -s "$checksum" ]; then
    echo "BLOCKED: $checksum is missing; build the ISO before signing" >&2
    exit 1
fi

# Sign the checksum file rather than each split part: the checksum covers the
# reassembled image, so one signature authenticates the whole download.
gpg --batch --yes --local-user "$CLAUSIS_SIGNING_KEY_ID" \
    --armor --detach-sign --output "$checksum.asc" "$checksum"
gpg --batch --yes --local-user "$CLAUSIS_SIGNING_KEY_ID" \
    --armor --export "$CLAUSIS_SIGNING_KEY_ID" > "$dist_dir/clausis-release-key.asc"

gpg --batch --verify "$checksum.asc" "$checksum"

echo "signed $checksum with $CLAUSIS_SIGNING_KEY_ID"
ls -l "$checksum.asc" "$dist_dir/clausis-release-key.asc"
