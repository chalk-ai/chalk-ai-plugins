#!/usr/bin/env bash
# Launcher that exec's `chalk-lsp` only when the current Claude Code project
# is a Chalk SDK project (i.e. has chalk.yaml at the project root). In any
# other project the launcher exits 0 so the LSP simply doesn't run.
#
# Expects the chalk-lsp binary to be on PATH. Install it via:
#   cargo install --path <chalk-rs>/chalk-lsp
# or by placing a prebuilt binary somewhere in PATH.
#
# Environment variables (all provided by Claude Code):
#   CLAUDE_PROJECT_DIR - current project root
#   CHALK_LSP_BIN      - optional override for the chalk-lsp binary

set -u

project_dir="${CLAUDE_PROJECT_DIR:-${PWD}}"

if [ ! -f "${project_dir}/chalk.yaml" ]; then
  # Not a Chalk SDK project; skip starting the language server.
  exit 0
fi

bin="${CHALK_LSP_BIN:-chalk-lsp}"

if ! command -v "${bin}" >/dev/null 2>&1 && [ ! -x "${bin}" ]; then
  echo "chalk-lsp: binary '${bin}' not found on PATH. Build it from chalk-rs/chalk-lsp or set CHALK_LSP_BIN." >&2
  exit 127
fi

exec "${bin}" "$@"
