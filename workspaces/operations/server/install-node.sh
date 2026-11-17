#!/usr/bin/env bash
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo 'Run as root' >&2
  exit 1
fi

version='v24.22.3'
archive="node-${version}-linux-x64.tar.xz"
base="https://nodejs.org/dist/${version}"
target="/opt/node-${version}"

if [[ ! -x "${target}/bin/node" ]]; then
  scratch=$(mktemp -d)
  trap 'rm -rf -- "$scratch"' EXIT
  curl -fL --retry 3 --output "${scratch}/${archive}" "${base}/${archive}"
  curl -fL --retry 3 --output "${scratch}/SHASUMS256.txt" "${base}/SHASUMS256.txt"
  (cd "$scratch" && grep " ${archive}$" SHASUMS256.txt | sha256sum --check --status)
  mkdir -p "$target"
  tar -xJf "${scratch}/${archive}" --strip-components=1 -C "$target"
fi

for binary in node npm npx corepack; do
  ln -sfn "${target}/bin/${binary}" "/usr/local/bin/${binary}"
done

node --version
npm --version
