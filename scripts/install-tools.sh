#!/usr/bin/env bash
set -euo pipefail
# Linux x86_64, AWS CloudShell / Google Cloud Shell.
mkdir -p "$HOME/bin"
TOOLS_TMP=$(mktemp -d)
trap 'rm -rf "$TOOLS_TMP"' EXIT
curl -fsSL https://releases.hashicorp.com/terraform/1.11.4/terraform_1.11.4_linux_amd64.zip -o "$TOOLS_TMP/terraform.zip"
unzip -oq "$TOOLS_TMP/terraform.zip" -d "$HOME/bin"
curl -fsSL https://github.com/grafana/k6/releases/download/v0.54.0/k6-v0.54.0-linux-amd64.tar.gz -o "$TOOLS_TMP/k6.tgz"
tar -xzf "$TOOLS_TMP/k6.tgz" -C "$TOOLS_TMP"
cp "$TOOLS_TMP/k6-v0.54.0-linux-amd64/k6" "$HOME/bin/k6"
echo 'En esta terminal ejecuta: export PATH="$HOME/bin:$PATH"'
