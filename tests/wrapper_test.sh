#!/usr/bin/env bash
# Integration test for plugins/chalk-lsp/bin/chalk-lsp.sh.
# Verifies the gating wrapper behaves correctly without exercising the real
# chalk-lsp binary: a mock CHALK_LSP_BIN stands in for the language server.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WRAPPER="${REPO_ROOT}/plugins/chalk-lsp/bin/chalk-lsp.sh"

if [ ! -x "${WRAPPER}" ]; then
  echo "FAIL: ${WRAPPER} is not executable" >&2
  exit 1
fi

pass=0
fail=0

run_case() {
  local name="$1" expected_code="$2"
  shift 2
  local got_code=0
  "$@" >/tmp/wrapper_out 2>/tmp/wrapper_err || got_code=$?
  if [ "${got_code}" = "${expected_code}" ]; then
    echo "PASS: ${name} (exit ${got_code})"
    pass=$((pass + 1))
  else
    echo "FAIL: ${name} (expected exit ${expected_code}, got ${got_code})" >&2
    echo "  stdout: $(cat /tmp/wrapper_out)" >&2
    echo "  stderr: $(cat /tmp/wrapper_err)" >&2
    fail=$((fail + 1))
  fi
}

TRUE_BIN="$(command -v true)"
FALSE_BIN="$(command -v false)"

# Case 1: no chalk.yaml at project root -> wrapper exits 0 without invoking the binary.
tmp_empty="$(mktemp -d)"
trap 'rm -rf "${tmp_empty}" "${tmp_chalk:-}"' EXIT
run_case "no chalk.yaml -> exit 0" 0 \
  env CLAUDE_PROJECT_DIR="${tmp_empty}" CHALK_LSP_BIN="${FALSE_BIN}" "${WRAPPER}"

# Case 2: chalk.yaml present, mock binary exits 0 -> wrapper exec's it (exit 0).
tmp_chalk="$(mktemp -d)"
touch "${tmp_chalk}/chalk.yaml"
run_case "chalk.yaml present, mock binary -> exec" 0 \
  env CLAUDE_PROJECT_DIR="${tmp_chalk}" CHALK_LSP_BIN="${TRUE_BIN}" "${WRAPPER}"

# Case 3: chalk.yaml present, binary not on PATH -> wrapper exits 127.
run_case "chalk.yaml present, binary missing -> 127" 127 \
  env CLAUDE_PROJECT_DIR="${tmp_chalk}" CHALK_LSP_BIN=/nonexistent/path/chalk-lsp PATH=/usr/bin:/bin "${WRAPPER}"

# Case 4: chalk.yaml present, mock that records its argv -> wrapper passes args through.
mock_log="$(mktemp)"
mock_bin="$(mktemp)"
cat >"${mock_bin}" <<EOF
#!/usr/bin/env bash
echo "args: \$*" > "${mock_log}"
exit 0
EOF
chmod +x "${mock_bin}"
run_case "args pass through to chalk-lsp" 0 \
  env CLAUDE_PROJECT_DIR="${tmp_chalk}" CHALK_LSP_BIN="${mock_bin}" "${WRAPPER}" --some-flag value
if [ "$(cat "${mock_log}")" = "args: --some-flag value" ]; then
  echo "PASS: argv recorded correctly"
  pass=$((pass + 1))
else
  echo "FAIL: argv mismatch, got: $(cat "${mock_log}")" >&2
  fail=$((fail + 1))
fi
rm -f "${mock_bin}" "${mock_log}"

echo
echo "wrapper_test.sh: ${pass} passed, ${fail} failed"
[ "${fail}" -eq 0 ]
