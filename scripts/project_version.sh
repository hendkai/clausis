#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=$(sed -n 's/^version = "\([0-9][0-9.]*\)"$/\1/p' "$project_dir/pyproject.toml")

case "$version" in
    [0-9]*.[0-9]*.[0-9]*) ;;
    *) printf '%s\n' "Ungültige oder fehlende Clausis-Version in pyproject.toml" >&2; exit 1 ;;
esac

printf '%s\n' "$version"
