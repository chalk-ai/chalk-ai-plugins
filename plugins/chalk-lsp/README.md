# chalk-lsp (Claude Code plugin)

Connects Claude Code to the `chalk-lsp` language server. Active only in
projects that have a `chalk.yaml` at the project root — in any other project
the plugin is a no-op.

## Prerequisite: install the `chalk-lsp` binary

The plugin does not bundle the binary. Install it from
[`chalk-rs/chalk-lsp`](https://github.com/chalk-ai/chalk-private) (private):

```sh
cd ~/chalk/chalk/chalk-rs
cargo install --path chalk-lsp
# Verify:
which chalk-lsp
```

`cargo install` drops the binary in `~/.cargo/bin/chalk-lsp`, which should
already be on your PATH.

If you keep the binary somewhere unusual, point the plugin at it:

```sh
export CHALK_LSP_BIN=/some/other/path/chalk-lsp
```

## Install the plugin

From inside Claude Code:

```
/plugin marketplace add chalk-ai/chalk-ai-plugins
/plugin install chalk-lsp@chalk-ai
```

## How the gating works

`bin/chalk-lsp.sh` is the `command` declared in `.lsp.json`. On every start it
checks `${CLAUDE_PROJECT_DIR}/chalk.yaml`:

- present → `exec chalk-lsp "$@"`, the LSP runs as normal
- absent  → `exit 0`, the LSP doesn't run and Claude Code moves on

`restartOnCrash` is `false`, so a project without `chalk.yaml` doesn't cause
restart loops.

## Files

| Path | Purpose |
| :-- | :-- |
| `.claude-plugin/plugin.json` | Plugin manifest; points at `./.lsp.json` |
| `.lsp.json` | LSP server config (command, `extensionToLanguage`, etc.) |
| `bin/chalk-lsp.sh` | Gating wrapper around the user-installed `chalk-lsp` |
