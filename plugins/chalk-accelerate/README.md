# chalk-accelerate (Claude Code / Codex plugin)

Teaches coding agents to make Chalk Python resolvers statically accelerable.
The plugin ships:

- `skills/accelerate-python-resolvers/SKILL.md` — the workflow and rewrite
  recipes (None guards, unsupported libraries, unbound locals).
- `bin/accelerator-diagnostics.py` — a stdlib-only script that exports the
  current Chalk project (`python -m chalk.cli export --proto`), sends the
  graph to the Chalk static accelerator service
  (`StaticAcceleratorService/GetStaticConversionDiagnostics`), and prints the
  returned LSP diagnostics as `file:line: severity: message`.

## How it works

The static accelerator service symbolically executes each resolver and
returns a diagnostic for every resolver it cannot fully convert to a native
columnar expression — including exactly *why* (e.g. `'int.__add__(int)' is
only supported for non-null values; guard this 'option<int>' argument against
None`). The skill loops: run script → rewrite resolver → re-run, until the
project reports `All resolvers are statically accelerable.`

## Configuration

| Setting | Default | Purpose |
| :-- | :-- | :-- |
| `CHALK_ACCELERATOR_HOST` (or `--host`) | `https://accelerator.chalk.ai` | Accelerator service endpoint. Chalk runs this service on your behalf; point it at a local server (e.g. `http://127.0.0.1:8780`) for development. |
| `CHALK_ACCELERATOR_TOKEN` | unset | Optional bearer token for the hosted service. |

## Requirements

- The project must be a Chalk SDK project (`chalk.yaml`/`chalk.yml` at the
  root) with `chalkpy` importable from the Python environment used to run the
  script.

## Install (Claude Code)

```
/plugin marketplace add chalk-ai/chalk-ai-plugins
/plugin install chalk-accelerate@chalk-ai
```

## Install (Codex)

```
codex plugin marketplace add chalk-ai/chalk-ai-plugins
codex plugin add chalk-accelerate@chalk-ai
```
