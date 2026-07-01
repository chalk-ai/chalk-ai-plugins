# chalk-plan-cache

Find and debug Chalk **query plan cache misses** straight from engine logs,
using the `chalk logs` CLI search.

Chalk caches a compiled plan the first time it plans a query, keyed by a
normalized `BatchQuery`. A miss forces the engine to replan on the hot path.
Misses are expected the first time a query shape is seen, but a query that
"looks identical" to a previous one yet keeps missing means some field in the
request is varying between calls — most often the `given_features` set.

## Skill

- **`debug-plan-cache-misses`** — locates the two miss-related log lines
  (`missed the plan cache` and `Computed plan for ... given ...`), then diffs
  consecutive plan computations to pinpoint which `BatchQuery` field differs
  and forces the miss.

## Usage

Ask Claude Code / Codex something like:

- "Why does this query keep missing the plan cache?"
- "Find plan cache misses for `sv5_idplus_features_parallel` in the last day."
- "This query is replanning on every request — debug it from the logs."

The skill drives `chalk logs`, e.g.:

```sh
chalk logs --query 'message:"missed the plan cache"' --start-time "24h ago"
chalk logs --query 'message:"Computed plan for" message:<query_name>' --start-time "24h ago"
```

Point `chalk` at the right environment first (via `chalk config` or
`--environment`). The skill only reads logs — it never mutates an environment.
