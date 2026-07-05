# context-balance

**MCP server that detects pruning-retrieval feedback loops in LLM agent context management.**

Part of the [Agentic Johari Window](../../README.md) framework.

## The problem it solves

Agent systems that manage context (retrieve, summarize, prune) can fall into a pathological feedback loop:

1. Agent retrieves aggressively → context bloats → quality drops
2. System prunes to recover → accidentally drops signal → agent misses needed context
3. Agent re-retrieves to compensate → context bloats again
4. Cycle repeats

Each individual step looks reasonable. The problem is the oscillation pattern, and nobody is watching for it.

## How it works

The MCP server exposes three instrumentation tools and three query tools.

### Instrumentation (call these from your agent)

| Tool | When to call |
|---|---|
| `log_retrieval(source, query, result_tokens, relevance_score?)` | When the agent retrieves context (RAG, file read, web fetch, memory recall, MCP resource) |
| `log_pruning(target, tokens_removed, reason, method)` | When context is removed (summarization, truncation, compression, explicit drop) |
| `log_quality_signal(metric, value, context_size?)` | When there's a quality measurement (eval score, user feedback, task success/failure, error) |

### Analysis (query these to check balance)

| Tool | What it returns |
|---|---|
| `get_balance_report(window?)` | Status (healthy/moderate/oscillating/critical), cycle count, re-retrievals, quality-correlated regret events, recommendation |
| `get_event_timeline(last_n?)` | Raw event log for debugging |
| `get_context_size_curve(last_n?)` | Context size over time with ASCII sparkline — shows oscillation visually |

### Detection algorithms

- **Oscillation detection** — tracks cumulative context size (retrievals minus pruning). A cycle is a full peak → trough → peak swing where both the drop and the rebound exceed 1000 tokens; a one-time prune-down is not counted.
- **Re-retrieval detection** — if the same source is retrieved, pruned, then retrieved again (in that order), that's the strongest signal of the feedback loop. Wasted tokens count only the retrievals that happen after a prune; the first retrieval was legitimate.
- **Quality correlation** — correlates quality drops with recent prunes (prune regret = lost signal) and recent retrievals (retrieval regret = added bloat).

## Installation

```bash
# From the repo
cd mcps/context-balance
pip install -e .

# Run
context-balance
```

### Claude Code configuration

Add to your Claude Code MCP settings:

```json
{
  "mcpServers": {
    "context-balance": {
      "command": "context-balance",
      "args": []
    }
  }
}
```

### Other MCP hosts

The server uses stdio transport. Any MCP-compatible host can connect.

## Example

```python
# In your agent code, instrument context operations:

# After a RAG retrieval
await mcp.call_tool("log_retrieval", {
    "source": "knowledge_base/product_docs",
    "query": "return policy",
    "result_tokens": 2400,
    "relevance_score": 0.82
})

# After summarizing old conversation
await mcp.call_tool("log_pruning", {
    "target": "conversation turns 1-15",
    "tokens_removed": 8500,
    "reason": "token limit approaching",
    "method": "summarize"
})

# After a task result
await mcp.call_tool("log_quality_signal", {
    "metric": "task_success",
    "value": 1.0,
    "context_size": 34000
})

# Check the balance
report = await mcp.call_tool("get_balance_report")
```

## Worked example

[`examples/synthetic_session.py`](./examples/synthetic_session.py) replays a scripted 24-event session through the real storage and detection layers: a RAG agent over-retrieves, summarizes away the docs it still needs under token pressure, then re-retrieves them. Run it yourself:

```bash
cd mcps/context-balance
PYTHONPATH=. python examples/synthetic_session.py
```

Actual output (not hand-written):

```json
{
  "status": "oscillating",
  "session_id": "synthetic-loop-demo",
  "total_events": 24,
  "total_retrievals": 11,
  "total_prunes": 5,
  "total_quality_signals": 8,
  "net_context_tokens": 18600,
  "cycles_detected": 2,
  "avg_cycle_period": 8.0,
  "re_retrievals": [
    {
      "source": "kb/product_docs",
      "times_retrieved": 3,
      "times_pruned": 2,
      "total_wasted_tokens": 5100,
      "first_seen_seq": 1,
      "last_seen_seq": 19
    },
    {
      "source": "kb/pricing",
      "times_retrieved": 2,
      "times_pruned": 1,
      "total_wasted_tokens": 1900,
      "first_seen_seq": 2,
      "last_seen_seq": 12
    }
  ],
  "prune_regret_events": 2,
  "retrieval_regret_events": 2,
  "recommendation": "Oscillating: 2 grow/shrink cycles detected. 'kb/product_docs' retrieved 3x and pruned 2x, wasting ~5100 tokens. System is in a prune-retrieve feedback loop. Pin critical context to prevent re-retrieval, or raise pruning staleness threshold."
}
```

The detector correctly separates the pathology from normal usage: `kb/product_docs` shows 5100 wasted tokens (the two post-prune re-retrievals, not the legitimate first one), while sources that were retrieved and pruned once without re-retrieval don't appear.

## Tests

```bash
cd mcps/context-balance
pip install -e ".[dev]"
python -m pytest tests/ -q
```

Unit tests feed synthetic event streams to the detection algorithms: pathological patterns (retrieve-prune-retrieve loops, repeated oscillation) must fire, healthy patterns (monotonic growth, one-time cleanup prunes, retrieve-retrieve-prune ordering) must not.

## Data storage

Events are stored in SQLite at `~/.context-balance/events.db`. Each session gets a unique ID. Data is local-only — no external dependencies, no cloud calls.

## License

MIT. See [LICENSE](../../LICENSE).
