---
name: context-health
description: Analyze the current conversation's context window health — categorize each block as Signal, Bloat, or Overhead, compute a Bloat Index, identify top bloat contributors, and report a staleness distribution. Use when the user asks to "check context health", "how bloated is my context", "context report", "bloat index", or when a long conversation feels like it's degrading.
---

# Context Health — The Bloat Index

Analyzes the current conversation's context composition and reports what percentage is working for the model (Signal) vs. working against it (Bloat) vs. fixed cost (Overhead).

## When to run

- User asks to check context health, bloat, or context quality
- Long conversation feels like it's degrading
- Before a critical task in a long session (check if context is clean enough)
- After completing a subtask (check if leftover context is now bloat)

## Procedure

### 1. Inventory the conversation

Walk through the entire visible conversation history. For each distinct block, record:

- **type**: one of `system_prompt`, `user_input`, `assistant_reasoning`, `tool_call`, `tool_result`, `retrieved_content`, `skill_output`, `mcp_resource`
- **turn**: which conversation turn it appeared in (number sequentially from 1)
- **description**: one-line summary of what the block contains (e.g., "git log output showing 15 commits", "file read of src/agent.py lines 1-200", "web search results for RAG failure modes")
- **approx_tokens**: estimate token count as `word_count × 1.3`, rounded to nearest 100
- **current_turn**: the turn number of this `/context-health` invocation

### 2. Assess staleness

For each block, determine `last_referenced_turn` — the most recent turn where:
- The user or assistant explicitly mentioned content from this block, OR
- A subsequent tool call used information that could only have come from this block, OR
- The block contains information that is still actively relevant to the current task

Compute `staleness = current_turn - last_referenced_turn`.

Staleness categories:
- **Fresh** (0-3 turns): recently used or still actively relevant
- **Aging** (4-10 turns): not recently referenced but may still be useful
- **Stale** (11+ turns): not referenced in a long time, likely dead weight

### 3. Assess task relevance

Determine the current active task (what the user is working on RIGHT NOW). For each block, assess:
- **Active**: directly relevant to the current task
- **Completed**: related to a prior task that is finished
- **Unrelated**: not connected to any current or recent task

### 4. Classify each block

Assign each block to a category:

**SIGNAL** — meets ALL of:
- Fresh or Aging staleness (0-10 turns)
- Active task relevance
- Substantive content (not just a short acknowledgment or status message)

**BLOAT** — meets ANY of:
- Stale (11+ turns) AND not actively relevant
- Completed task relevance (leftover from finished work)
- Superseded by newer information (e.g., an old file read replaced by a newer read of the same file)
- Large tool output that was only partially used (e.g., 3000-token file read where 2 lines were relevant)
- Verbose assistant reasoning from a resolved question

**OVERHEAD** — fixed costs that are neither signal nor bloat:
- System prompt / CLAUDE.md content
- Skill instructions (including these instructions)
- MCP tool schemas
- Base conversation framing

Note: Overhead is not "bad" — it's the cost of having capabilities available. But it IS a tax on the token budget that should be tracked.

### 5. Compute scores

```
signal_tokens = sum of approx_tokens for all SIGNAL blocks
bloat_tokens = sum of approx_tokens for all BLOAT blocks
overhead_tokens = sum of approx_tokens for all OVERHEAD blocks
total_tokens = signal_tokens + bloat_tokens + overhead_tokens

signal_pct = round(100 × signal_tokens / total_tokens)
bloat_pct = round(100 × bloat_tokens / total_tokens)
overhead_pct = round(100 × overhead_tokens / total_tokens)

bloat_index = round(bloat_tokens / signal_tokens, 2)
```

Bloat Index interpretation:
- **< 0.5**: Healthy. More than 2x signal to bloat.
- **0.5 - 1.0**: Moderate. Bloat is significant but not dominant.
- **1.0 - 2.0**: Unhealthy. Bloat exceeds signal. Pruning recommended.
- **> 2.0**: Critical. Context is mostly noise. Consider new conversation or aggressive summarization.

### 6. Identify top bloat contributors

List the 3-5 largest BLOAT blocks by token count. For each:
- What it is (type + description)
- Which turn it's from
- How many tokens it occupies
- Why it's bloat (stale, completed task, superseded, partially used)

### 7. Compute staleness distribution

Count blocks in each staleness category:
- Fresh (0-3 turns): N blocks, X% of tokens
- Aging (4-10 turns): N blocks, X% of tokens
- Stale (11+ turns): N blocks, X% of tokens

### 8. Output the report

Print the report directly to the user. Use this format:

```
Context Health Report — turn {current_turn}

Estimated context: ~{total_tokens} tokens

  SIGNAL     {bar}  {signal_pct}%  (~{signal_tokens} tokens)
  BLOAT      {bar}  {bloat_pct}%   (~{bloat_tokens} tokens)
  OVERHEAD   {bar}  {overhead_pct}% (~{overhead_tokens} tokens)

  Bloat Index: {bloat_index} — {interpretation}

  Top bloat contributors:
  1. {type} from turn {N} (~{tokens} tokens) — {reason}
  2. ...
  3. ...

  Staleness:
  Fresh (0-3 turns):   {bar}  {pct}%
  Aging (4-10 turns):  {bar}  {pct}%
  Stale (11+ turns):   {bar}  {pct}%

  {recommendation}
```

For the bars, use filled/empty block characters scaled to 16 characters total.

For the recommendation, choose based on bloat_index:
- < 0.5: "Context is healthy. No action needed."
- 0.5-1.0: "Context is accumulating bloat. Consider summarizing completed work."
- 1.0-2.0: "Bloat exceeds signal. Recommend starting a new conversation or summarizing aggressively before the next complex task."
- > 2.0: "Context is critically bloated. Start a fresh conversation for best results."

## Important notes

- **This is an approximation.** You cannot read the raw token buffer. You're analyzing visible conversation artifacts. Say this in the report footer.
- **System compression is invisible.** Claude Code automatically compresses prior messages near context limits. Compressed content is not visible to this analysis. If compression has occurred, note it.
- **Don't count your own analysis as bloat.** This skill's output should not be included in the inventory.
- **Be honest about uncertainty.** If you can't determine whether a block is Signal or Bloat, classify it as Signal (conservative — don't over-report bloat).
- **Keep the analysis fast.** Don't re-read files or run tools to verify block contents. Work from what's already in the conversation.
- **Token estimates are rough.** Note "estimates based on word count × 1.3" in the report footer.

## Example invocations

- `/context-health` — full analysis of current conversation
