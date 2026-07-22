# chalk-deploy-function

Deploy a stand-alone python function to Chalk's container infrastructure
using the **`chalkcompute`** SDK (`@chalkcompute.function()`).

The decorator builds a container image, uploads it, and registers the
function at import time; calling the decorated function invokes it remotely
and returns the result.

## Skill

- **`deploy-chalk-function`** — walks through writing a self-contained
  `uv run --script` python file that declares a `chalkcompute.function`,
  the required credential env vars, and the common pitfalls (bare decorator,
  missing `CHALK_ENVIRONMENT_ID`, PyO3 Python version ceiling).

## Usage

Ask Claude Code / Codex something like:

- "Deploy this python function as a chalk function."
- "Run this function remotely on Chalk's infrastructure."
- "Why am I getting `permission_denied` from `GetOrBuildCustomImage`?"

## Requirements

- `uv` installed (scripts use a `uv run --script` shebang).
- Chalk credentials exported as env vars: `CHALK_API_SERVER`,
  `CHALK_CLIENT_ID`, `CHALK_CLIENT_SECRET`, `CHALK_ENVIRONMENT_ID`
  (readable from `chalk config` for the current project).
