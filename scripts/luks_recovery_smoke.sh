#!/bin/sh
set -eu

builder=${CLAUSIS_BUILDER_IMAGE:-clausis-iso-builder:recovery-test}

docker run --rm --platform linux/amd64 --entrypoint sh "$builder" -exc '
    image=$(mktemp)
    recovery=$(mktemp)
    trap '\''rm -f "$image" "$recovery"'\'' EXIT HUP INT TERM

    truncate -s 32M "$image"
    printf old-clausis-test-secret \
        | cryptsetup luksFormat --type luks2 --batch-mode --key-file=- "$image"
    printf "%s\n" \
        "1234-5678-9012-3456-7890-1234-5678-9012-3456-7890-1234-5678" \
        >"$recovery"
    chmod 0600 "$recovery"
    printf old-clausis-test-secret \
        | cryptsetup luksAddKey --key-file=- "$image" "$recovery"
    cryptsetup open --test-passphrase --key-file "$recovery" "$image"
'

printf '%s\n' "LUKS2 recovery-key enrollment and unlock verified."
