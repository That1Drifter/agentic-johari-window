# The Agentic Johari Window — and What to Build From It

*A short piece on borrowing a 1955 psychology model to think about AI agent transparency, and the concrete tools that fall out of it.*

## The mental model nobody's using

In 1955, Joseph Luft and Harrington Ingham proposed a 2×2 for interpersonal awareness: things you know about yourself vs. things others know. Four quadrants — Open, Blind Spot, Hidden, Unknown — and a simple dynamic: you grow the Open quadrant through **feedback** (what others tell you) and **disclosure** (what you tell them).

Seventy years later, the AI agent observability industry is quietly rebuilding this model without naming it. Langfuse logs traces. Arize Phoenix runs evals. Anthropic publishes red-team results. Each vendor is chasing one corner of the same square, but nobody has drawn the square.

So let's draw it. Map **agent internal state** against **operator visibility**:

```
                    OPERATOR
                Visible      Not Visible
              ┌───────────┬───────────┐
    Surfaced  │   OPEN    │  HIDDEN   │
  A  by agent │ (aligned) │ (opaque)  │
  G           ├───────────┼───────────┤
  E  Not      │   BLIND   │  UNKNOWN  │
  N  surfaced │   SPOT    │(emergent) │
  T           │  (drift)  │           │
              └───────────┴───────────┘
```

- **OPEN** — structured CoT, logged tool calls, declared confidence. The goal state.
- **BLIND SPOT** — drift, bias, hallucination patterns. The agent can't see them; external evals can.
- **HIDDEN** — implicit reasoning, dropped context, near-miss decisions. The agent "has" it; the operator doesn't.
- **UNKNOWN** — emergent failure modes, multi-turn jailbreaks, capability overhang. Neither side sees it coming.

Three forces grow Open: **Feedback** shrinks Blind Spot, **Disclosure** shrinks Hidden, **Exploration** shrinks Unknown.

## How I got here

Two things put me on this path.

The first was Destin Sandlin's *Smarter Every Day* episode [*What Everyone Sees... But I don't (The Johari Window)*](https://youtu.be/WtQ64nSbdY4) — SED 314. Destin walks through the 1955 Luft-Ingham model with his friend Rev. Daylan Woodall, who'd taught him the concept years earlier. Destin's framing was *"I cannot quit thinking about it."* Same. I watched the episode and my brain immediately started running the model against LLMs instead of people. The agent has things it knows that I don't know it knows. I can see patterns in its behavior it can't see in itself. And there's a fourth region neither of us can reach. At one point Daylan teases Destin — *"You're just totally thinking about this as an engineer. We've got a system."* Guilty as charged; this document is the system.

The second was Andy Clark's *The Experience Machine*, which argues the brain is a prediction engine generating a controlled hallucination — most of what you perceive is a guess, and only a thin summary reaches conscious report. The massive subconscious computation and the narrow surfaced trace are different animals. That picture kept rhyming with what I was seeing in LLMs: massive activation-space computation, a narrow text output, and a big gap in between.

Put the two together and the move was obvious. Destin handed me the vocabulary. Clark told me why the gap exists in the first place. I went looking for somebody who'd already applied the Johari Window to AI agents and couldn't find anyone. So here we are.

## Why this isn't just a metaphor

Two things make the framing more than cute.

First, **the literature backs the structural claim**. Cemri et al.'s 2025 multi-agent failure taxonomy found that 58% of failures in multi-agent systems happen at or after inter-agent handoffs — exactly where the Johari framing predicts new Hidden and Unknown zones get created. Every summarization between agents is a quadrant transition, and practitioners are watching it go wrong at scale.

Second, **the quadrants pre-date AI**. Nisbett & Wilson showed in 1977 that humans routinely confabulate reasons for their own choices — plausible prose explanations that have nothing to do with the actual cause. Gazzaniga's split-brain work found the left hemisphere inventing stories to explain actions driven by the right. Andy Clark's predictive processing frames conscious experience as a thin surfaced slice of massive subconscious computation. When Anthropic's 2025 paper shows Claude 3.7 Sonnet only verbalizing hint usage 41% of the time, that's not a uniquely-AI failure. That's a cognitive system doing what cognitive systems do.

Which means: building agents that assume prose chain-of-thought is reliable disclosure is the same category error as assuming humans have full introspective access. In SED 314, Daylan gives the best one-line definition of the Hidden quadrant I've heard: *"not the lie you're telling people, but the truth you're withholding."* That is exactly the shape of CoT unfaithfulness. The model isn't lying in its verbalized reasoning. It's producing a plausible summary of a vastly richer computation it didn't — and often couldn't — surface. The Hidden quadrant is not a bug to engineer out. It's a property of any system that computes more than it can report on.

## Tools that fall out of the framework

Here's where the framing gets operational. Each quadrant and force points at concrete gaps in current tooling.

### 1. `johari-boundary-auditor` (MCP server)

**Derived from**: multi-agent compounding + Hidden quadrant at handoffs.

Every existing observability tool treats agent-to-agent handoffs as "just another span." But MAST says the boundary is where failures live. This MCP instruments handoffs as first-class objects: it captures the full pre-summary context, the post-summary context passed to the next agent, and the diff. Operators can see exactly what got dropped, when, and by which agent. Directly targets the 58% failure band nobody's instrumenting.

### 2. `/disclosure-check` (skill)

**Derived from**: Disclosure force + CoT unfaithfulness tension.

Given a CoT trace, this skill runs Turpin/Lanham-style faithfulness tests automatically. It paraphrases the CoT, injects biasing hints, re-runs the query, and measures whether the stated reasoning actually predicts the answer change. Output: a faithfulness score that treats prose CoT as weighted evidence rather than ground truth. Turns "we log reasoning" from false reassurance into a number you can put on a dashboard.

### 3. `/johari-diagnostic` (skill)

**Derived from**: all four quadrants, applied as a coverage audit.

Points the skill at an agent repo and it scores observability coverage across all four quadrants: Open (tracing), Blind Spot (evals), Hidden (provenance, structured output), Unknown (red-team, adversarial tests). Outputs something like `Open 8/10, Blind Spot 2/10 (no evals), Hidden 1/10 (no provenance), Unknown 0/10 (no red-team)`. Turns a vague "we need better observability" into a prioritized gap list.

### 4. `near-miss-recorder` (MCP, experimental)

**Derived from**: Hidden quadrant + "the agent almost did X" signal.

Captures tool-call candidates the agent considered but didn't execute. The hardest tool of the four because it depends on the agent surfacing its deliberation, which — per the faithfulness research — may itself be unreliable. Ship it as experimental and pair with a faithfulness check.

## What the framework is *for*

The Agentic Johari Window isn't a replacement for tracing, evals, or red-teaming. It's the **shared vocabulary** that tells you which one you need next. Right now, an engineering team arguing about observability gaps has no common language — one person wants more logging, another wants more evals, another wants adversarial tests, and nobody can explain why they're not the same thing.

The quadrants explain why they're not the same thing. The forces explain why you need all three. And the tools above are the first pass at making each force something you can install.

---

*Part of an open framework in progress. Framework writeup, interactive diagnostic, and literature review are in the [repo]. Feedback, disclosure, and exploration all welcome.*
