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

- **Oscillation detection** — tracks cumulative context size (retrievals minus pruning). If size cycles grow/shrink repeatedly with amplitude > 1000 tokens, flags oscillation.
- **Re-retrieval detection** — if the same source is retrieved, pruned, then retrieved again, that's the strongest signal of the feedback loop. Reports wasted tokens.
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

Example balance report:

```json
{
  "status": "oscillating",
  "total_events": 47,
  "total_retrievals": 22,
  "total_prunes": 18,
  "total_quality_signals": 7,
  "net_context_tokens": 12400,
  "cycles_detected": 4,
  "avg_cycle_period": 8.3,
  "re_retrievals": [
    {
      "source": "knowledge_base/product_docs",
      "times_retrieved": 3,
      "times_pruned": 2,
      "total_wasted_tokens": 7200
    }
  ],
  "prune_regret_events": 2,
  "retrieval_regret_events": 5,
  "recommendation": "Oscillating: 4 grow/shrink cycles detected. 'knowledge_base/product_docs' retrieved 3x and pruned 2x, wasting ~7200 tokens. System is in a prune-retrieve feedback loop. Pin critical context to prevent re-retrieval, or raise pruning staleness threshold."
}
```

## Data storage

Events are stored in SQLite at `~/.context-balance/events.db`. Each session gets a unique ID. Data is local-only — no external dependencies, no cloud calls.

## License

MIT. See [LICENSE](../../LICENSE).
