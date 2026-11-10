#!/usr/bin/env bash
# Download the official Godot 4 Linux binary for gdcheck (used by action.yml and the sandbox test),
# and verify its SHA-512 before it is unpacked.
# Part of godot-skill-check. By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
# Env: GODOT_VERSION (default 4.7.2), RUNNER_TEMP (default /tmp), GITHUB_ENV (optional),
#      GODOT_SHA512 (optional: the expected SHA-512 of the zip; if unset, it is read from the
#      SHA512-SUMS.txt that the Godot team publishes with the same release).
set -euo pipefail
v="${GODOT_VERSION:-4.7.2}"
case "$v" in
  *[!0-9.]*|"") echo "gdcheck: bad Godot version '$v' (use numbers like 4.7.2)" >&2; exit 2 ;;
esac
d="${RUNNER_TEMP:-/tmp}/gdcheck-godot-$v"
bin="$d/godot"
zip="Godot_v${v}-stable_linux.x86_64.zip"
base="https://github.com/godotengine/godot/releases/download/${v}-stable"
if [ ! -x "$bin" ]; then
  mkdir -p "$d"
  echo "gdcheck: downloading $base/$zip"
  curl -fsSL --retry 3 -o "$d/godot.zip" "$base/$zip"
  want="${GODOT_SHA512:-}"
  if [ -z "$want" ]; then
    curl -fsSL --retry 3 -o "$d/SHA512-SUMS.txt" "$base/SHA512-SUMS.txt"
    want="$(awk -v f="$zip" '$2 == f || $2 == "*" f {print $1}' "$d/SHA512-SUMS.txt" | head -1)"
    rm -f "$d/SHA512-SUMS.txt"
  fi
  if [ -z "$want" ]; then
    echo "gdcheck: no SHA-512 for $zip in $base/SHA512-SUMS.txt (set GODOT_SHA512)" >&2
    rm -f "$d/godot.zip"; exit 3
  fi
  got="$(python3 -c 'import hashlib, sys; print(hashlib.sha512(open(sys.argv[1], "rb").read()).hexdigest())' "$d/godot.zip")"
  if [ "$(printf '%s' "$want" | tr 'A-F' 'a-f')" != "$got" ]; then
    echo "gdcheck: SHA-512 mismatch for $zip: expected $want, got $got" >&2
    rm -f "$d/godot.zip"; exit 3
  fi
  echo "gdcheck: SHA-512 verified: $got"
  python3 -m zipfile -e "$d/godot.zip" "$d"
  mv "$d/Godot_v${v}-stable_linux.x86_64" "$bin"
  chmod +x "$bin"
  rm -f "$d/godot.zip"
fi
"$bin" --headless --version
if [ -n "${GITHUB_ENV:-}" ]; then
  echo "GDCHECK_GODOT=$bin" >> "$GITHUB_ENV"
fi
echo "GDCHECK_GODOT=$bin"
