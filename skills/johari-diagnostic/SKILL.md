---
name: johari-diagnostic
description: Audit an AI agent project for observability coverage across the four Agentic Johari Window quadrants — Open, Blind Spot, Hidden, Unknown. Detects tracing, evals, provenance, red-teaming, and related signals in the codebase and produces a scored gap report. Use when the user asks to "run a johari diagnostic", "audit agent observability", "score quadrant coverage", or "where are my observability gaps".
---

# Johari Diagnostic

Audits an AI agent codebase for observability coverage across the four quadrants of the Agentic Johari Window, produces a scored report, and identifies the largest gap.

Framework reference: *The Agentic Johari Window* — four quadrants (OPEN, BLIND SPOT, HIDDEN, UNKNOWN) with three expansion forces (Feedback, Disclosure, Exploration).

## When to run

The user wants to know where their agent system's observability is weakest. Typical triggers:
- "Run a johari diagnostic"
- "Audit my agent's observability"
- "Score my quadrant coverage"
- "What's in my blind spot?"
- Generic request to "review observability" of an AI agent project.

If the target directory is unclear, ask once. Otherwise default to the current working directory.

## Procedure

### 1. Establish scope

Identify the target directory. Detect the primary language(s) — run `Glob` for `**/*.py`, `**/*.ts`, `**/*.tsx`, `**/*.js`, `**/pyproject.toml`, `**/package.json`. Note which ecosystems are present; signal patterns differ between Python and JS/TS.

If there's an obvious AI agent entry point (e.g., `agent.py`, `main.py`, `src/agents/`), note it. A non-agent project gets a diagnostic saying "this doesn't look like an agent codebase" and exits.

### 2. Detect signals across all 16 dimensions

Run the detections below. **Run independent Grep/Glob calls in parallel** — many dimensions share no dependencies. Each dimension scores one of:
- **STRONG** → full weight (the capability is clearly present in runtime code, not just tests)
- **PARTIAL** → half weight (present in tests, one-off usage, config-only, or commented out)
- **ABSENT** → zero

For each dimension, record: the evidence found (file paths + matched patterns) or a note that nothing matched. Capture specific file:line references.

---

#### OPEN quadrant (max weight 6)

**1. `tracing` (weight 2) — tool calls and I/O in structured traces**
- Imports / deps: `langfuse`, `phoenix`, `arize`, `langsmith`, `opentelemetry`, `wandb.weave`, `braintrust`, `logfire`, `helicone`, `honeycomb`, `datadog`
- Decorators: `@observe`, `@trace`, `@weave.op`, `@tracer.start_as_current_span`
- Env vars: `LANGFUSE_`, `LANGSMITH_`, `PHOENIX_`, `OTEL_`, `BRAINTRUST_API_KEY`
- Config files: `otel-*.yaml`, `langfuse.config.*`
- STRONG if at least one tracing library is imported and used in runtime code. PARTIAL if only present in tests or a single `print`/`logger.info` wrapping tool calls. ABSENT otherwise.

**2. `reasoning` (weight 2) — structured CoT / reasoning traces**
- Structured output fields: `"reasoning"`, `"thought"`, `"rationale"`, `"justification"`, `"chain_of_thought"`
- Prompt patterns: `"think step by step"`, `"explain your reasoning"`, `<thinking>`
- API params: `reasoning_effort`, `extended_thinking`, `thinking=`
- Pydantic/Zod schemas with a reasoning field
- STRONG if structured reasoning is captured (schema field or extended-thinking enabled). PARTIAL if just a prompt instruction with no capture. ABSENT otherwise.

**3. `confidence` (weight 1) — declared confidence / uncertainty**
- Fields: `"confidence"`, `"certainty"`, `"uncertainty"`, `"probability"`, `"logprob"`
- API params: `logprobs=True`, `top_logprobs`
- Patterns like `confidence: "high"|"medium"|"low"` in output schemas
- STRONG if confidence is captured per-decision. PARTIAL if logprobs are requested but unused. ABSENT otherwise.

**4. `versioning` (weight 1) — prompts, model versions, configs tied to decisions**
- Prompt version strings, prompt files in a `prompts/` dir with version suffixes
- Pinned model IDs (e.g., `claude-opus-4-6-20260101` not `claude-opus-4-6`)
- Langfuse prompt management, Humanloop, PromptLayer
- Git SHA or config hash captured in logs
- STRONG if version metadata is attached to logged decisions. PARTIAL if pinned but not logged. ABSENT if only unpinned model strings.

---

#### BLIND SPOT quadrant (max weight 6) — Feedback force

**5. `evals` (weight 2) — eval pipelines or LLM-as-judge**
- Dirs: `evals/`, `eval/`, `evaluations/`, `benchmarks/`
- Imports: `ragas`, `deepeval`, `promptfoo`, `trulens`, `langsmith.evaluation`, `braintrust.eval`, `inspect_ai`
- Pytest markers: `@pytest.mark.eval`, files named `eval_*.py` or `*_eval.py`
- Config files: `promptfoo.yaml`, `ragas.yaml`, `inspect_ai.toml`
- CI workflow files that run evals on PRs
- STRONG if there's a runnable eval suite. PARTIAL if only a single eval script or test. ABSENT otherwise.

**6. `drift` (weight 2) — behavioral drift monitoring**
- Imports: `evidently`, `whylabs`, `alibi-detect`, `nannyml`, `deepchecks`
- Baseline files: `baseline_metrics.json`, `golden_*.json`
- Scheduled comparison jobs, metric history tables
- STRONG if baseline comparison runs on a schedule. PARTIAL if baselines exist but no scheduled comparison. ABSENT otherwise.

**7. `anomaly` (weight 1) — anomaly detection on agent metrics**
- Imports: `pyod`, `isolation_forest`, statistical outlier detection
- Alerting configs: PagerDuty, Opsgenie, Grafana alert rules on agent metrics
- Thresholds on latency/error/cost metrics with alerting
- STRONG if alerting is wired to agent-specific metrics. PARTIAL if generic infra alerts only. ABSENT otherwise.

**8. `human_review` (weight 1) — human review loop**
- Imports: `label-studio`, `argilla`, `prodigy`
- Dirs: `annotations/`, `reviews/`, `human_feedback/`
- API routes: `/feedback`, `/annotate`, `/review`, `/thumbs`
- Langfuse annotation queues, Braintrust human eval, LangSmith feedback APIs
- STRONG if there's a running review queue or feedback endpoint. PARTIAL if only a static form. ABSENT otherwise.

---

#### HIDDEN quadrant (max weight 6) — Disclosure force

**9. `context_provenance` (weight 2) — trace which docs influenced a decision**
- Citation fields: `source_id`, `document_id`, `citation`, `sources`, `provenance`, `references`
- RAG libs with citation mode: `llama-index` citation query engine, `langchain` source metadata, `llamaindex` `CitationQueryEngine`
- Output schemas with a `sources` / `citations` array
- STRONG if retrieved sources are attached to decisions at runtime. PARTIAL if metadata is stored but not surfaced in output. ABSENT if retrieval is bare text-only.

**10. `step_audit` (weight 2) — detect silent step-skipping**
- Workflow frameworks: `langgraph`, `temporal`, `prefect`, `dagster`, state machines, `xstate`
- Checkpoint patterns: `checkpoint`, `state_hash`, step completion tracking, workflow IDs
- Explicit per-step logging with step names
- STRONG if workflow state is persisted per-step. PARTIAL if only start/end logged. ABSENT if the agent runs as a single black-box call.

**11. `inter_agent` (weight 1) — audit what context is passed/dropped at handoffs**
- Multi-agent frameworks: `autogen`, `crewai`, `langgraph`, `openai.swarm`, `mcp-server`, `anthropic-mcp`
- Handoff logging between agents, message audit trails
- Schemas validating inter-agent messages
- Only applies if the project is multi-agent. If single-agent, score N/A and exclude from denominator.
- STRONG if handoffs are logged with full pre/post context. PARTIAL if only summaries logged. ABSENT if messages pass unobserved.

**12. `near_miss` (weight 1) — detect near-miss harmful actions**
- Pre-execution filters: `tool_filter`, `pre_call_hook`, `guard`, `validator`
- Safety libs: `nemo-guardrails`, `llm-guard`, `lakera`, `guardrails-ai`
- Patterns: "rejected tool call", "blocked action", "denied by policy"
- STRONG if filtered-but-considered actions are logged separately from executed ones. PARTIAL if actions are filtered but not logged. ABSENT otherwise.

---

#### UNKNOWN quadrant (max weight 6) — Exploration force

**13. `red_team` (weight 2) — adversarial testing**
- Dirs: `red_team/`, `adversarial/`, `jailbreak/`, `attacks/`
- Libs: `garak`, `pyrit`, `promptbench`, `deepteam`, `giskard`
- Fixture files with prompt-injection attempts, jailbreak strings
- STRONG if there's a runnable adversarial suite. PARTIAL if one-off test file. ABSENT otherwise.

**14. `chaos` (weight 2) — degraded-condition testing**
- Fault injection: mock failures, `responses` / `nock` / `msw` simulating API errors
- Test fixtures with stale data, timeouts, partial responses, malformed tool outputs
- Chaos libs: `chaoslib`, `litmus`
- STRONG if agent behavior is tested under degraded dependencies. PARTIAL if only happy-path mocks. ABSENT otherwise.

**15. `multi_agent_emergent` (weight 1) — emergent coordination / feedback loop tests**
- Loop detection in multi-agent configs: max iteration limits, cycle detectors
- Tests that exercise multi-turn agent conversations for pathological patterns
- Only applies if multi-agent. N/A if single-agent.
- STRONG if loop/coordination tests exist. PARTIAL if only iteration caps. ABSENT otherwise.

**16. `fail_safe` (weight 1) — circuit breakers / safe failure modes**
- Circuit breakers: `pybreaker`, `circuit-breaker`, `resilience4j`, `opossum`
- Timeouts: explicit `timeout=`, `deadline=`, `abort_signal`
- Kill switches: feature flags, `ENABLED=false` toggles for emergency shutoff
- Graceful degradation: try/except with fallback models or cached responses
- STRONG if multiple patterns present. PARTIAL if only timeouts. ABSENT otherwise.

---

### 3. Score

For each quadrant, compute:
```
score = Σ(weight × multiplier)
multiplier = 1.0 if STRONG, 0.5 if PARTIAL, 0 if ABSENT
max_score = Σ(weight) for applicable dimensions  (skip N/A)
pct = round(100 × score / max_score)
```

Overall coverage = mean of the four quadrant percentages.

Identify the **largest gap** = quadrant with the lowest percentage. If tied, prefer HIDDEN > BLIND SPOT > UNKNOWN > OPEN (Hidden is the highest-stakes quadrant per the framework).

### 4. Report

Produce two outputs:

**A. Inline summary** — print this to the user directly. Keep it tight:

```
Johari Diagnostic — <target dir>

◉ OPEN          ██████░░░░  62%   (tracing ✓, reasoning ✓, confidence ·, versioning ✗)
◐ BLIND SPOT    ███░░░░░░░  33%   (evals ✓, drift ✗, anomaly ✗, human_review ·)
◑ HIDDEN        █░░░░░░░░░  17%   (provenance ✗, step_audit ·, inter_agent n/a, near_miss ✗)
○ UNKNOWN       ░░░░░░░░░░   0%   (red_team ✗, chaos ✗, emergent n/a, fail_safe ✗)

Overall: 28%
Largest gap: UNKNOWN — expand via Exploration (red-teaming, chaos engineering)
```

Legend: `✓` = strong, `·` = partial, `✗` = absent, `n/a` = not applicable.

**B. Written report** — save to `johari-report.md` in the target directory. Structure:

```markdown
# Johari Diagnostic Report

**Target:** <path>
**Date:** <YYYY-MM-DD>
**Overall coverage:** <pct>%

## Quadrant scores

| Quadrant | Score | Expand via |
|---|---|---|
| OPEN (Aligned) | <pct>% | — (goal state) |
| BLIND SPOT (Drift) | <pct>% | Feedback |
| HIDDEN (Opaque) | <pct>% | Disclosure |
| UNKNOWN (Emergent) | <pct>% | Exploration |

## Largest gap: <QUADRANT> (<pct>%)

<One paragraph explaining what's missing and why it matters per the framework.>

**Recommended next steps:**
- <Specific action tied to a missing dimension>
- <...>

## Findings by dimension

### OPEN

#### ✓ tracing (STRONG, 2/2)
Evidence: `src/agent.py:12` imports `langfuse`, `@observe` decorators on 4 tool call sites.

#### ✗ versioning (ABSENT, 0/1)
No prompt version strings, pinned model IDs, or config hashes found. Models referenced as unpinned strings (e.g., `model="gpt-4"` at `src/llm.py:23`).

<...continue for all 16 dimensions...>

## Notes

- Dimensions marked N/A (not applicable) were excluded from scoring. This happens for multi-agent-specific dimensions when the project is single-agent.
- This diagnostic detects *presence* of capabilities, not *quality*. A "STRONG" tracing score means tracing exists; it doesn't mean it's being used well.

---
Generated by the `johari-diagnostic` skill. Framework: The Agentic Johari Window.
```

## Important notes for the agent running this

- **Parallelize detections.** The 16 dimensions are independent. Run Grep/Glob calls in parallel batches, not sequentially.
- **Runtime code vs tests matters.** A pattern in `tests/` counts as PARTIAL unless it's also present in the runtime code path. Use Glob to exclude `**/test*/**` and `**/*test*` from STRONG detections and then re-scan tests-only for PARTIAL credit.
- **Language-specific.** If the project is pure TypeScript, skip Python-only libraries (e.g., `pyod`) and vice versa. The goal is to avoid false negatives from checking for Python libs in a JS codebase.
- **Don't invent signals.** If nothing matches, the dimension is ABSENT. Don't infer from comments, docs, or README aspirations.
- **Don't score quality.** STRONG means "the capability is wired up." It does not mean "the capability is working well." The report should note this explicitly.
- **Be honest about false positives.** If a pattern is matched in an unused file, a vendored library, or a commented-out line, downgrade to PARTIAL or ABSENT and note it in the finding.
- **Max one pass.** Don't loop trying to improve the score. One audit, one report.
- **Report length.** Inline summary ≤ 15 lines. Written report ≤ 400 lines. Don't pad.

## Example invocations

- `/johari-diagnostic` → audit current working directory
- `/johari-diagnostic ./my-agent` → audit a specific path
- `/johari-diagnostic --quadrant hidden` → focused audit of one quadrant (detect only the 4 dimensions in that quadrant)
