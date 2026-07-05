# The Context Window Is the Johari Window

**A framework for reasoning about what's in your LLM's context window, what's missing, and what's in the way.**

Every LLM system in production has the same two complaints: the context gets polluted with stale noise, and the model doesn't have what it needs. These are not independent problems; the first one causes the second. Map **context relevance** against **context presence** and you get a 2×2:

```
                     CONTEXT RELEVANCE
               Right context      Wrong/stale context
            ┌─────────────────┬─────────────────┐
  Present   │     SIGNAL      │     BLOAT       │
  in window │   (effective)   │   (rot/noise)   │
            ├─────────────────┼─────────────────┤
  Absent    │     NEEDED      │     UNKNOWN     │
  from      │   (retrievable) │  (undiscovered) │
  window    │                 │                 │
            └─────────────────┴─────────────────┘
```

Three forces grow the Signal quadrant:

- **Pruning** shrinks **Bloat**: context hygiene, selective compression, staleness detection
- **Retrieval** shrinks **Needed**: RAG, structured memory, MCP resources
- **Exploration** shrinks **Unknown**: proactive search, discovering what you don't know you're missing

The core claim is mechanical, not metaphorical: the window is finite and zero-sum, and bloat doesn't just waste tokens, it **displaces signal**. Chroma's 2025 context-rot study found every one of 18 frontier models degrades well before the context limit, driven partly by distractor interference. Every token of noise pushes a token of signal out of the window or into the attention dead zone. Bloat creates the Needed quadrant. That's why the framework's contrarian claim is that **what you take out matters more than what you put in.**

Full argument: [`context-window-writeup.md`](./context-window-writeup.md).

## What's in this repo

### The framework (v0.2)

| File | What it is |
|---|---|
| [`context-window-writeup.md`](./context-window-writeup.md) | The main writeup: the 2×2, the displacement mechanism, the zero-sum tradeoff, multi-agent fragmentation, temporal decay |
| [`research-context-window.md`](./research-context-window.md) | Literature review backing the v0.2 claims: context rot, lost-in-the-middle, token-budget reasoning, MAST handoff failures |

### Derived tools

| Tool | What it does |
|---|---|
| [`skills/context-health/`](./skills/context-health/SKILL.md) | Claude Code skill that audits the current conversation: categorizes each context block as Signal, Bloat, or Overhead, computes a Bloat Index, and recommends what to prune. Token counts are an approximation, not a measurement; where the host exposes real context accounting, prefer that |
| [`mcps/context-balance/`](./mcps/context-balance/README.md) | MCP server that detects pruning-retrieval feedback loops: oscillation cycles, re-retrieval of pruned sources, quality drops correlated with prunes or retrievals. Ships with a unit-tested detection layer |
| [`skills/johari-diagnostic/`](./skills/johari-diagnostic/SKILL.md) | v0.1 skill that inspects an agent repo and scores observability coverage from evidence |
| [`agentic-johari-window.jsx`](./agentic-johari-window.jsx) | v0.1 interactive React diagnostic: a 16-question self-audit across the four quadrants |

## Where this came from (v0.1)

The project started as an adaptation of the 1955 Luft-Ingham Johari Window to AI agent observability: **agent internal state** mapped against **operator visibility**, giving Open, Hidden, Blind Spot, and Unknown quadrants with Feedback, Disclosure, and Exploration as the expansion forces. That framing still works for the abstract question of agent transparency, but the context window is where the quadrants actually live, so v0.2 reframed the whole thing mechanically.

The v0.1 material is kept intact:

| File | What it is |
|---|---|
| [`agentic-johari-window.md`](./agentic-johari-window.md) | The v0.1 framework writeup: quadrants, forces, multi-agent compounding |
| [`sample-writeup.md`](./sample-writeup.md) | Shorter blog-style version with the personal origin story |
| [`research.md`](./research.md) | v0.1 literature review, ~40 sources across AI safety, interpretability, cognitive science, and multi-agent failure research |

## Status

**v0.2: context-window reframe + two working tools.** The context-health skill and context-balance MCP server ship in this repo. Next up: a worked end-to-end example running context-balance against a real agent session, and adapters so agent frameworks can emit `log_*` events without hand-instrumentation.

## Origin

Inspired by Destin Sandlin's *Smarter Every Day* episode 314, [*What Everyone Sees... But I don't (The Johari Window)*](https://youtu.be/WtQ64nSbdY4), which dropped 2026-04-11 and wouldn't leave me alone. If you're here because of that video: welcome, this is the agent version of what Destin and Daylan were talking about.

Andy Clark's *The Experience Machine* and decades of predictive-processing cognitive science provide the structural argument for why these quadrants pre-exist AI, and why expecting LLMs to self-report faithfully via chain-of-thought is the same category error as expecting humans to have full introspective access. See [`research.md`](./research.md) §11 for that thread. Tor Nørretranders' *The User Illusion* supplies the v0.2 parallel: consciousness is a bandwidth bottleneck, a context window for the mind.

## Prior art check

No prior work was found applying the Johari Window to AI agents or LLM context management. The closest precedent is [Adam Shostack's threat-modeling adaptation](https://shostack.org/blog/threat-modeling-through-the-johari-window/) for cybersecurity. No observability vendor (Langfuse, Arize Phoenix, LangSmith, W&B Weave, Braintrust, Galileo) uses Johari framing. If you've seen this applied elsewhere and I missed it, open an issue; I'd like to cite it.

## License

Framework writeups and documentation: [CC BY 4.0](./LICENSE-DOCS).
Code (React diagnostic, skills, MCP servers): [MIT](./LICENSE).

## Contributing

Pruning, retrieval, and exploration all welcome.

- **Issues**: corrections to the framework, missing citations, prior art I should know about
- **PRs**: tools, adapters for specific agent frameworks (LangGraph, CrewAI, AutoGen), additional quadrant examples
- **Discussion**: if you've applied this to a real agent system, I'd love to hear how it landed

---

*Roger Maxwell ("Drifter"). v0.1 2026-04-11, v0.2 2026-04-13.*
