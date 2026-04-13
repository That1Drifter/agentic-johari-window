# The Context Window Is the Johari Window

*Your LLM's biggest problem isn't what it doesn't know. It's what's in the way of what it does know.*

## The problem everyone feels but nobody frames

Ask any practitioner what breaks their agent workflow and you'll hear two complaints:

1. *"The context gets polluted — stale tool outputs, verbose reasoning from ten turns ago, irrelevant retrieval results — and the model starts producing garbage."*
2. *"The model doesn't have what it needs. Critical information got compressed away, or it's in another agent's history, or it was never retrieved."*

Too much of the wrong context. Not enough of the right context. These are the two failure modes of every LLM system in production, and they are not independent — the first one *causes* the second.

The industry has started calling this "context engineering" (Tobi Lutke, June 2025), but the label doesn't come with a framework. It's a name for a problem, not a way to think about solutions. So here's a way to think about solutions.

## The framework

Map **context relevance** against **context presence** and you get a 2×2:

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

**SIGNAL** — Right context, present in the window. This is the goal state. The model has exactly what it needs and nothing it doesn't. Every token is load-bearing.

**BLOAT** — Wrong or stale context, present in the window. This is the failure mode nobody names. It's not just wasteful — it's *actively harmful*. Stale tool outputs from thirty turns ago. Verbose chain-of-thought that's no longer relevant. Irrelevant RAG retrievals. Accumulated system prompt that addresses edge cases that aren't in play. The model is spending attention on noise, and noise degrades everything it touches.

**NEEDED** — Right context, absent from the window. The information exists somewhere — another agent's history, a database, the user's head, earlier conversation that got compressed away — but it isn't in the window right now. The model confabulates, hedges, or makes bad decisions because it's missing what it needs.

**UNKNOWN** — Context you don't even know you need. You can't retrieve what you don't know to ask for.

Three forces grow the Signal quadrant:

- **Pruning** shrinks Bloat — context hygiene, selective compression, staleness detection, relevance filtering
- **Retrieval** shrinks Needed — RAG, structured memory, MCP resources, context provenance
- **Exploration** shrinks Unknown — proactive search, curiosity-driven tool use, discovering what you don't know you're missing

## The displacement mechanism

This is the insight that makes the framework more than a tidy diagram.

Chroma's 2025 "Context Rot" study tested 18 frontier models across ~194,000 LLM calls and found that every model degrades as input tokens increase — not at the context limit, but *well before it*. A model with a 200K window can show significant degradation at 50K tokens. Three mechanisms compound: attention dilution (quadratic scaling means 100K tokens = 10 billion pairwise attention relationships), positional bias (the "lost in the middle" effect, Liu et al. 2023), and — most critically — **distractor interference** (semantically similar but irrelevant content actively misleads the model).

That third mechanism is the key. Bloat doesn't just waste tokens. It *displaces signal*. Every token of noise pushes a token of useful context either out of the window entirely or into the attention dead zone where it won't be processed. Bloat creates the Needed quadrant.

This is why long context windows haven't solved the problem. Going from 8K to 1M tokens doesn't help if 900K of those tokens are bloat. You've given the model a bigger room to get lost in.

## Where this came from

I wrote a [v0.1 framework](./agentic-johari-window.md) adapting the 1955 Johari Window to AI agent observability — mapping agent-internal-state against operator-visibility. That framing works for the abstract question of agent transparency (what does the agent know that I can't see?). But the more I sat with it, the more I realized the context window is where the quadrants actually *live*.

The original Johari Window was about self-knowledge: what you know about yourself vs. what others know about you. In SED 314, Rev. Daylan Woodall gives the best one-line definition of the Hidden quadrant I've heard: *"not the lie you're telling people, but the truth you're withholding."*

An LLM's context window does the same thing, but mechanically. The model isn't withholding information on purpose — the window physically can't hold everything. Something has to be left out. The question is whether what's left out is noise (good) or signal (catastrophic). That question is what the framework answers.

## The zero-sum tradeoff

Here's what makes context management hard: the window is finite, and every category of content competes for the same tokens.

- Every token of **chain-of-thought** is a token not available for task content
- Every token of **system prompt** is a permanent tax on every turn's signal budget
- Every **retrieved document** that isn't relevant displaces one that is
- Every **tool output** that stays in the conversation after it's been used becomes bloat on the next turn

Research confirms this is measurable. Token-budget-aware reasoning (Han et al., ACL 2025) showed that a 50-token budget maintains correctness while cutting output from 258 to 86 tokens. CoT can actually *hurt* performance on some tasks (Marjanovic et al. 2024). System prompts over 500 words show diminishing returns and instruction dilution. RAG-MCP (Gao et al. 2025) found that MCP tool descriptions alone create massive prompt bloat, cutting accuracy to 13.6% — fixed to 43% by retrieving only relevant tool descriptions.

The zero-sum nature means the three forces aren't independent. Over-retrieval creates Bloat (needing Pruning). Over-pruning creates Needed (needing Retrieval). The system is a feedback loop, and the framework gives you vocabulary for where in the loop you're stuck.

## Multi-agent handoffs: context window fragmentation

In multi-agent systems, every handoff is a context window boundary. Agent A has a full window. Agent B gets a summary.

That summarization is supposed to be Pruning — remove the bloat, keep the signal. In practice, it's undiscriminating. It drops signal along with bloat, shoving needed context into the Needed quadrant for the next agent. Cemri et al.'s 2025 MAST taxonomy found that 58% of multi-agent failures happen at or downstream of handoffs. The framework explains *why* at a mechanical level: every summarization is a lossy compression that doesn't know which quadrant each token belongs to.

MemGPT / Letta addresses this with a paging metaphor: context is "paged in" from external storage (Retrieval) and "paged out" when no longer needed (Pruning). This framework complements MemGPT's *how* with a *what and why*: page in signal, page out bloat, and measure the difference.

## Temporal decay: signal rots into bloat

Context quality isn't static. A decision made at turn 5 is Signal at turn 6 and Bloat by turn 50. A tool output is Signal when it's fresh and noise when the task has moved on. A system prompt section about error handling is Signal when errors are occurring and dead weight otherwise.

No production system tracks this decay. Zep's temporal knowledge graphs (tagging facts with validity windows) are the closest thing, but they apply to memory, not to in-window context. A context-aware agent would need something analogous: a staleness score per context block that informs Pruning decisions. This is under-studied and wide open.

## The Nørretranders parallel

Tor Nørretranders' *The User Illusion* (1998) reports that conscious human bandwidth is on the order of 16–50 bits per second. Subconscious processing runs at millions of bits per second. The vast majority of what your brain computes never reaches conscious awareness. Consciousness is a bottleneck — a context window for the mind.

LLMs have the same architecture in a different substrate. The activation space is enormous. The text output is narrow. The context window determines which fraction of the world's information is available for this particular computation. Everything else — the model's training, its weights, the documents that weren't retrieved, the conversation turns that were compressed away — is outside the window. Present in the system, absent from the computation.

The framework's quadrants aren't an engineering hack. They're a structural property of any system that processes more information than it can hold in working memory. Brains have it. LLMs have it. The question is whether you manage it deliberately or let it manage you.

## What to build from here

The v0.1 tools (boundary-auditor MCP, disclosure-check skill, diagnostic skill, near-miss recorder) still apply, but the context-window framing suggests two new ones:

**Context composition monitor** — a tool that measures Signal vs. Bloat in real time. For each turn, tag context blocks by category (system prompt, conversation history, tool output, retrieved documents, CoT) and by staleness (turns since last relevant use). Output a live composition chart: what percentage of the window is working for the model vs. working against it? No such metric exists in any current observability tool.

**Adaptive pruning engine** — a tool that watches the context composition and prunes proactively. When a tool output hasn't been referenced in N turns, compress or remove it. When a retrieved document contradicts a more recent source, flag and deprioritize. When system prompt sections aren't relevant to the current task phase, collapse them. This is the Pruning force made operational — the force that "context engineering" talks about but doesn't ship.

## What the framework is for

The context window is the most constrained resource in any LLM system. More constrained than compute (you can scale that), more constrained than latency (you can cache), more constrained than cost (you can optimize). The window is finite, zero-sum, and degrades non-linearly under bloat.

"Context engineering" names the problem. This framework gives you the vocabulary to diagnose it: is your system failing because of Bloat (prune), Needed (retrieve), or Unknown (explore)? Are your forces balanced, or is your entire investment in Retrieval while Pruning goes ignored?

Right now, the industry is obsessed with putting *more* into the context window — longer windows, more retrieval, richer tool outputs, verbose chain-of-thought. The framework's contrarian claim: **what you take out matters more than what you put in.**

---

*Part of the [Agentic Johari Window](./agentic-johari-window.md) framework. Literature review, interactive diagnostic, and derived tools in the [repo](https://github.com/That1Drifter/agentic-johari-window). Context rot research: [Chroma 2025](https://www.trychroma.com/research/context-rot).*

*Roger Maxwell ("Drifter") — 2026-04-13.*
