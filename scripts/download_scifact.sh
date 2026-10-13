#!/usr/bin/env bash
set -euo pipefail

# Reproduce the exact official SciFact archive audited in Phase 0.
# Usage: ./scripts/download_scifact.sh [destination]

destination="${1:-data/raw/scifact}"
archive_sha256="11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be"
url="https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
license_url="https://raw.githubusercontent.com/allenai/scifact/68b98a56d93e0f9da0d2aab4e6c3294699a0f72e/LICENSE.md"
license_sha256="56ee69bc639cbab8f0b2e4b67091ec5e9390aa99a1d65f0a35e4274686c9a806"

mkdir -p "$destination"
temporary_directory="$(mktemp -d)"
trap 'rm -rf "$temporary_directory"' EXIT

curl --fail --location --silent --show-error "$url" -o "$temporary_directory/data.tar.gz"
actual_sha256="$(shasum -a 256 "$temporary_directory/data.tar.gz" | awk '{print $1}')"
if [[ "$actual_sha256" != "$archive_sha256" ]]; then
  echo "Checksum mismatch: expected $archive_sha256, got $actual_sha256" >&2
  exit 1
fi

tar -xzf "$temporary_directory/data.tar.gz" -C "$temporary_directory"
cp -R "$temporary_directory/data/." "$destination/"
curl --fail --location --silent --show-error "$license_url" -o "$temporary_directory/LICENSE.md"
actual_license_sha256="$(shasum -a 256 "$temporary_directory/LICENSE.md" | awk '{print $1}')"
if [[ "$actual_license_sha256" != "$license_sha256" ]]; then
  echo "License checksum mismatch: expected $license_sha256, got $actual_license_sha256" >&2
  exit 1
fi
cp "$temporary_directory/LICENSE.md" "$destination/SCIFACT_LICENSE.md"
echo "SciFact data verified and copied to $destination"
