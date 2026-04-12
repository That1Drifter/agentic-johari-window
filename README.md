# The Agentic Johari Window

**A framework for reasoning about what your AI agents know, hide, and can't see.**

The 1955 Luft–Ingham Johari Window mapped self-knowledge against others' knowledge across four quadrants. This project adapts it to AI agents: **agent internal state** against **operator / system visibility**.

```
                OPERATOR
            Visible      Not Visible
          ┌───────────┬───────────┐
  Agent   │   OPEN    │  HIDDEN   │
 surfaces │ (aligned) │ (opaque)  │
          ├───────────┼───────────┤
  Agent   │   BLIND   │  UNKNOWN  │
 doesn't  │   SPOT    │(emergent) │
          │  (drift)  │           │
          └───────────┴───────────┘
```

Three expansion forces grow the Open quadrant:

- **Feedback** (evals, LLM-as-judge, anomaly detection) shrinks **Blind Spot**
- **Disclosure** (structured CoT, reasoning traces, context provenance) shrinks **Hidden**
- **Exploration** (red-teaming, chaos engineering, adversarial testing) shrinks **Unknown**

In multi-agent systems, every handoff creates new Hidden and Unknown zones. (Cemri et al. 2025 found 58% of multi-agent failures happen at or downstream of inter-agent handoffs.)

## What's in this repo

| File | What it is |
|---|---|
| [`agentic-johari-window.md`](./agentic-johari-window.md) | The full framework writeup — quadrants, forces, multi-agent compounding, practical application |
| [`sample-writeup.md`](./sample-writeup.md) | A shorter blog-style version with the personal origin story |
| [`research.md`](./research.md) | Literature review — ~40 sources from AI safety, interpretability, cognitive science, and multi-agent failure research. Covers where the framework is supported and where the literature complicates it |
| [`agentic-johari-window.jsx`](./agentic-johari-window.jsx) | Interactive React diagnostic — a 16-question self-audit that scores agent systems across the four quadrants |
| [`skills/johari-diagnostic/SKILL.md`](./skills/johari-diagnostic/SKILL.md) | First derived tool — a Claude Code skill that inspects a real agent repo and scores observability coverage from evidence (not a survey) |

## Status

**v0.1 — concept + writeup + research + first tool.** This is the conceptual foundation and the first derived tool. Three more tools are planned (see the framework doc for details):

- `/disclosure-check` — CoT faithfulness tests (Turpin / Lanham / Chen-style) as a skill
- `johari-boundary-auditor` — MCP server that instruments inter-agent handoffs as first-class objects
- `near-miss-recorder` — experimental MCP for capturing considered-but-not-executed tool calls

## Origin

Inspired by Destin Sandlin's *Smarter Every Day* episode 314 — [*What Everyone Sees... But I don't (The Johari Window)*](https://youtu.be/WtQ64nSbdY4) — which dropped 2026-04-11 and wouldn't leave me alone. If you're here because of that video: welcome, this is the agent version of what Destin and Daylan were talking about.

Andy Clark's *The Experience Machine* and decades of predictive-processing cognitive science provide the structural argument for why these quadrants pre-exist AI — and why expecting LLMs to self-report faithfully via chain-of-thought is the same category error as expecting humans to have full introspective access. See [`research.md`](./research.md) §11 for that thread.

## Prior art check

No prior work was found applying the Johari Window to AI agents or LLM observability. The closest precedent is [Adam Shostack's threat-modeling adaptation](https://shostack.org/blog/threat-modeling-through-the-johari-window/) for cybersecurity. No observability vendor (Langfuse, Arize Phoenix, LangSmith, W&B Weave, Braintrust, Galileo) uses Johari framing. If you've seen this applied elsewhere and I missed it, open an issue — I'd like to cite it.

## License

Framework writeups and documentation: [CC BY 4.0](./LICENSE-DOCS).
Code (React diagnostic, skills, MCP servers): [MIT](./LICENSE).

## Contributing

Feedback, disclosure, and exploration all welcome.

- **Issues** — corrections to the framework, missing citations, prior art I should know about
- **PRs** — tools, adapters for specific agent frameworks, additional quadrant examples
- **Discussion** — if you've applied this to a real agent system, I'd love to hear how it landed

---

*Roger Maxwell ("Drifter") — 2026-04-11.*
