# chalk-ai-plugins

Private plugin marketplace for the `chalk-ai` GitHub org. Distributes plugins
to both [Claude Code](https://code.claude.com/docs/en/plugin-marketplaces) and
[Codex](https://developers.openai.com/codex/plugins) from a single repository.

## Repository layout

```
chalk-ai-plugins/
├── .claude-plugin/
│   └── marketplace.json        # Claude Code marketplace catalog
├── .agents/
│   └── plugins/
│       └── marketplace.json    # Codex marketplace catalog
└── plugins/
    ├── chalk-hello/            # Example starter plugin (Claude + Codex)
    │   ├── .claude-plugin/plugin.json
    │   ├── .codex-plugin/plugin.json
    │   └── skills/chalk-hello/SKILL.md
    └── chalk-lsp/              # chalk-lsp language server (Claude Code only)
        ├── .claude-plugin/plugin.json
        ├── .lsp.json
        ├── bin/chalk-lsp.sh
        └── README.md
```

Plugins that work for both runtimes ship both a `.claude-plugin/plugin.json`
and a `.codex-plugin/plugin.json`. Plugins that only make sense for one
runtime (e.g. `chalk-lsp`, since Codex does not support LSP servers) ship
just one manifest and are registered in only the matching marketplace catalog.

## Install

Using `gh skill`

```sh
gh skill install chalk-ai/chalk-ai-plugins
```

Choose all skills -> Enter -> Choose your coding agents -> Enter -> Installation scope: Global: install in home directory (available everywhere)

## Install (Claude Code)

```sh
/plugin marketplace add chalk-ai/chalk-ai-plugins
/plugin install chalk-hello@chalk-ai
```

Private-repo auth: Claude Code uses your local git credentials. For background
auto-updates, export a token with `repo` scope:

```sh
export GITHUB_TOKEN=ghp_...
```

To prompt teammates to install the marketplace automatically in a given
project, add this to that project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "chalk-ai": {
      "source": { "source": "github", "repo": "chalk-ai/chalk-ai-plugins" }
    }
  }
}
```

## Install (Codex)

```sh
codex plugin marketplace add chalk-ai/chalk-ai-plugins
codex plugin add chalk-hello@chalk-ai
```

Codex reads `.agents/plugins/marketplace.json` from the repo root.

## Add a new plugin

1. `mkdir -p plugins/<plugin-name>/{.claude-plugin,.codex-plugin,skills/<skill-name>}`
2. Create `plugins/<plugin-name>/.claude-plugin/plugin.json` (name, version, description).
3. Create `plugins/<plugin-name>/.codex-plugin/plugin.json` (same fields plus `skills`, `interface`).
4. Add a `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`).
5. Register the plugin in **both** marketplace catalogs:
   - Append an entry to `.claude-plugin/marketplace.json`'s `plugins` array (relative-path `source`).
   - Append an entry to `.agents/plugins/marketplace.json`'s `plugins` array (`git-subdir` source pinned to `main`).
6. Bump `version` in both `plugin.json` files on every release — Claude Code and Codex skip updates when the version string is unchanged.
7. Validate locally before pushing:

   ```sh
   claude plugin validate .
   ```

## Notes

- Marketplace name `chalk-ai` is the public identifier users see when running
  `/plugin install <plugin>@chalk-ai`.
- This repo is private; pushes are visible only to chalk-ai org members.
