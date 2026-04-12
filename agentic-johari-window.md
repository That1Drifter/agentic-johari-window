# The Agentic Johari Window

### A Framework for Understanding What Your AI Agents Know, Hide, and Can't See

---

## The Problem

As AI agents move from demos into production — making decisions, calling tools, collaborating with other agents — a critical gap has emerged: **we don't have a shared mental model for reasoning about agent transparency.**

The observability industry is building excellent tooling for traces, logs, and metrics. But tooling without a conceptual framework leads to instrumentation without insight. Teams add logging everywhere and still get surprised by failures.

We need a way to think about *what kind* of visibility gap we're dealing with — not just that one exists.

## The Framework

The **Agentic Johari Window** adapts the classic 1955 Luft-Ingham interpersonal awareness model to AI agent systems. The original Johari Window maps self-knowledge against others' knowledge across four quadrants. The adaptation maps **agent internal state** against **operator/system visibility** to classify transparency gaps in agentic workflows.

```
                    OPERATOR / SYSTEM
                 Visible          Not Visible
              ┌─────────────────┬─────────────────┐
    Surfaced  │                 │                 │
    by Agent  │     OPEN        │     HIDDEN      │
              │   (Aligned)     │   (Opaque)      │
  A           │                 │                 │
  G           ├─────────────────┼─────────────────┤
  E           │                 │                 │
  N   Not     │   BLIND SPOT    │    UNKNOWN      │
  T   Surfaced│   (Drift)       │   (Emergent)    │
              │                 │                 │
              └─────────────────┴─────────────────┘
```

### Quadrant 1: OPEN (Aligned)

**The agent surfaces it. The operator can see it.**

This is the goal state. Structured chain-of-thought, logged tool calls, explicit reasoning traces, declared confidence levels. When an agent says "I'm calling the database API with these parameters because the user asked for Q3 revenue" — and the observability stack captures that full chain — you're in the Open quadrant.

**Expanding this quadrant is the primary objective**, just as in the interpersonal model.

*Examples:*
- Traced tool invocations with input/output logging
- Explicit reasoning steps in structured output
- Declared uncertainty or confidence scores
- Version-pinned prompts and model snapshots tied to decisions

### Quadrant 2: BLIND SPOT (Drift)

**The operator/system can detect it. The agent cannot self-assess it.**

These are emergent behavioral patterns visible through external evaluation but invisible to the agent itself. An agent can't know that its tool selection has drifted 15% toward a particular API over the last week, or that its outputs have become subtly more verbose, or that it's hallucinating at a higher rate on Tuesdays when a particular data source is stale.

This quadrant is addressed by **feedback mechanisms**: eval pipelines, LLM-as-judge patterns, behavioral anomaly detection, session-level coherence scoring, and human review.

*Examples:*
- Gradual output quality degradation undetectable per-request
- Systematic bias in tool selection or retrieval ranking
- Latent prompt injection vulnerabilities discovered by red-teaming
- Performance patterns correlated with external state (time, data freshness)

### Quadrant 3: HIDDEN (Opaque)

**The agent "has" the information. The operator can't see it.**

The most dangerous quadrant for production systems. This includes implicit reasoning the model performs but doesn't surface: why it chose path A over path B, what latent context influenced a decision, what retrieved documents it weighted heavily, what it "almost" did before settling on an action.

In multi-agent systems, this compounds: Agent A passes a summary to Agent B, discarding context that would have changed Agent B's decision. The information existed in the system but was hidden by architecture.

This quadrant is addressed by **disclosure mechanisms**: structured chain-of-thought requirements, mandatory reasoning traces, context provenance tracking, and inter-agent message auditing.

*Examples:*
- Implicit assumptions from retrieved documents not cited in output
- Silent step-skipping in multi-step workflows
- Context window state influencing decisions with no external signal
- Inter-agent communication that drops critical context through summarization
- "Near-miss" decisions — the agent almost took a harmful action but didn't, and nobody knows

### Quadrant 4: UNKNOWN (Emergent)

**Neither the agent nor the operator can identify it.**

Novel failure modes, unknown-unknowns, and emergent behaviors that arise from the interaction of components nobody predicted. A multi-turn jailbreak that exploits a pattern nobody thought to test. A tool combination that produces correct-looking but catastrophically wrong results. An agent-to-agent feedback loop that amplifies a subtle error.

This quadrant can only be *reduced*, never eliminated. It's addressed by **exploration mechanisms**: adversarial testing, chaos engineering for agents, diverse red-teaming, anomaly detection with broad signal capture, and — critically — designing systems that fail safely when encountering the unknown.

*Examples:*
- Multi-turn escalation attacks (e.g., Crescendo-style jailbreaks)
- Emergent coordination behaviors in multi-agent systems
- Novel tool misuse patterns not covered by existing evals
- Compounding errors across agent boundaries that individually look benign
- Capability overhang — the agent can do something nobody realized it could do

## The Dynamics

Like the original Johari Window, the quadrants are not static. The goal is to **expand Open** by applying two forces:

### Feedback → Shrinks Blind Spots
External evaluation, monitoring, and review systems that detect what the agent can't self-report. This is the traditional observability play: traces, evals, anomaly detection. But framed as Johari feedback, it becomes clear that the *purpose* of observability isn't just debugging — it's expanding the agent's effective self-awareness by proxy.

### Disclosure → Shrinks Hidden
Architectural and prompting patterns that force agents to surface their reasoning. Structured output schemas, mandatory chain-of-thought, tool-use justification requirements, context provenance, inter-agent message logging. This isn't just "more logging" — it's designing agents that are constitutionally transparent.

### Exploration → Shrinks Unknown
Adversarial testing, red-teaming, chaos engineering, and broad anomaly detection. You can't instrument what you don't know exists, so this quadrant requires proactive probing rather than passive observation.

```
  ┌──────────────┐
  │    OPEN      │◄─── Feedback (evals, monitoring)
  │  (expanding) │◄─── Disclosure (structured reasoning)
  │              │◄─── Exploration (red-teaming, chaos)
  └──────────────┘
        ▲ ▲ ▲
        │ │ │
        │ │ └── UNKNOWN shrinks via Exploration
        │ └──── HIDDEN shrinks via Disclosure
        └────── BLIND SPOT shrinks via Feedback
```

## Multi-Agent Compounding

In single-agent systems, you have one Johari Window to manage. In multi-agent systems, every agent has its own window, and **inter-agent boundaries create new Hidden and Unknown zones**.

When Agent A summarizes context for Agent B:
- Agent A's Open quadrant may be large — it logged everything it did
- But the summarization itself creates a Hidden zone for Agent B: context that existed but wasn't passed
- And neither agent may be aware of what was lost — that's a new Unknown

This is analogous to the interpersonal Johari insight that group dynamics multiply awareness gaps. A team of five people doesn't have 5 windows — it has 5×4 = 20 directional awareness relationships.

**Design implication**: Multi-agent observability needs to instrument the *boundaries*, not just the agents. Every handoff is a potential quadrant transition.

## Practical Application

### For Agent Developers
Use the four quadrants as a checklist during design review:
1. **Open**: What is my agent explicitly logging and surfacing? Is it sufficient?
2. **Blind Spot**: What eval pipelines detect behavioral drift my agent can't self-report?
3. **Hidden**: What reasoning does my agent perform that isn't captured anywhere?
4. **Unknown**: What adversarial testing have I done? Where are my known unknowns?

### For Platform/Ops Teams
Map your observability stack to the quadrants:
- Tracing platforms (Langfuse, Arize, W&B Weave) → primarily Open quadrant
- Eval pipelines and LLM-as-judge → Blind Spot quadrant
- Structured output enforcement and context provenance → Hidden quadrant
- Red-teaming and anomaly detection → Unknown quadrant

If your entire observability investment is in tracing, you're only expanding one quadrant.

### For Consulting / Client Education
The Johari Window is already widely understood in organizational contexts. Saying "your agent has a large Hidden quadrant" is immediately intuitive to a business stakeholder in a way that "you need better chain-of-thought logging" is not.

## What Comes Next

This framework is the conceptual foundation. The practical tooling layer includes:

- **Agentic Johari Diagnostic**: An interactive tool for mapping agent workflows to the four quadrants and identifying which expansion mechanisms are missing
- **johari-agent-mcp**: An MCP server that instruments agentic workflows with Johari-aware classification, logging observations into the four quadrants in real-time
- **Quadrant Coverage Scoring**: A metric for evaluating how well an agent system's observability covers all four quadrants, not just Open

---

*The Agentic Johari Window is an open framework. Contributions, critiques, and extensions are welcome.*

*Created by Roger — [GitHub] | [Blog]*

---

## References

- Luft, J. & Ingham, H. (1955). "The Johari Window: A Graphic Model of Interpersonal Awareness." *Proceedings of the Western Training Laboratory in Group Development.* UCLA.
- The agent observability landscape (Langfuse, Arize Phoenix, W&B Weave, Galileo, Braintrust) addresses aspects of all four quadrants but lacks a unifying conceptual model.
- Rumsfeld's Known-Unknowns matrix, itself derived from the Johari Window, has been applied to AI knowledge categorization but not to agent workflow transparency.
