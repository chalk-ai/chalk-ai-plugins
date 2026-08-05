# chalk-benchmark-model

Benchmark the throughput and cost-per-token of a model served on vLLM in Chalk's
container infrastructure.

## Skill

- `benchmark-vllm-model` — end-to-end method: serve the model on a GPU, drive it
  to saturation, verify with DCGM that the GPU (not the client or the network) is
  the limiter, price the node from GCP's Cloud Billing Catalog, and compute
  $/1M tokens and $/1M requests.

Ships a reusable load generator at
`skills/benchmark-vllm-model/scripts/bench.py` that sweeps prompt length and
concurrency and reads throughput from vLLM's own Prometheus counters.

## Install

```sh
/plugin marketplace add chalk-ai/chalk-ai-plugins
/plugin install chalk-benchmark-model@chalk-ai
```

## Example

```
> what would it cost us to self-host Shieldstral-1.0-3B?
```

The skill covers the traps that make naive answers wrong: prefix caching
inflating input-token throughput, GPU accelerators being billed as a separate SKU
from vCPU/RAM (a 3x error if omitted), load generators that bottleneck before the
GPU does, and saturation numbers being quoted as if they were production costs.
