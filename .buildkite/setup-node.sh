#!/usr/bin/env bash
# Install a hermetic Node toolchain and configure npm to use build-local
# cache/prefix directories so we don't trip on root-owned files left by
# prior builds in the shared agent $HOME.
#
# Source this script (don't exec it) so the exported PATH/env vars affect
# the calling shell:
#   source .buildkite/setup-node.sh
set -euo pipefail

NODE_VERSION="${NODE_VERSION:-20.18.0}"
NODE_DIR="${HOME}/node-${NODE_VERSION}"

if [ ! -x "${NODE_DIR}/bin/node" ]; then
  echo "--- :node: Installing Node ${NODE_VERSION}"
  curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
    | tar -C /tmp -xJf -
  rm -rf "${NODE_DIR}"
  mv "/tmp/node-v${NODE_VERSION}-linux-x64" "${NODE_DIR}"
fi

export PATH="${NODE_DIR}/bin:${PATH}"

# Build-local npm cache + global install prefix avoids root-owned files
# in ~/.npm from earlier pipeline runs on the shared agent.
export NPM_CONFIG_CACHE="${PWD}/.npm-cache"
export NPM_CONFIG_PREFIX="${PWD}/.npm-prefix"
mkdir -p "${NPM_CONFIG_CACHE}" "${NPM_CONFIG_PREFIX}"
export PATH="${NPM_CONFIG_PREFIX}/bin:${PATH}"

echo "node:  $(node --version)"
echo "npm:   $(npm --version)"
echo "cache: ${NPM_CONFIG_CACHE}"
echo "prefix:${NPM_CONFIG_PREFIX}"
