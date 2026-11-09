#!/usr/bin/env bash
# Download the official Godot 4 Linux binary for gdcheck (used by action.yml and the sandbox test).
# Part of godot-skill-check. By MV2 of Munim, Inc. Made with AI agents (Anthropic Claude).
# SPDX-License-Identifier: Apache-2.0
# Env: GODOT_VERSION (default 4.7.2), RUNNER_TEMP (default /tmp), GITHUB_ENV (optional).
set -euo pipefail
v="${GODOT_VERSION:-4.7.2}"
case "$v" in
  *[!0-9.]*|"") echo "gdcheck: bad Godot version '$v' (use numbers like 4.7.2)" >&2; exit 2 ;;
esac
d="${RUNNER_TEMP:-/tmp}/gdcheck-godot-$v"
bin="$d/godot"
if [ ! -x "$bin" ]; then
  mkdir -p "$d"
  url="https://github.com/godotengine/godot/releases/download/${v}-stable/Godot_v${v}-stable_linux.x86_64.zip"
  echo "gdcheck: downloading $url"
  curl -fsSL --retry 3 -o "$d/godot.zip" "$url"
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
