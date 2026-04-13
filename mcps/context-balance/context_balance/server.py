"""Context Balance MCP Server.

Detects pruning-retrieval feedback loops in LLM agent context management.
Part of the Agentic Johari Window framework.
"""

import json
import uuid
from typing import Any

from mcp.server.fastmcp import FastMCP

from .detection import build_report
from .schemas import (
    EventType,
    PruningEvent,
    PruningMethod,
    QualityEvent,
    RetrievalEvent,
)
from .storage import EventStore

mcp = FastMCP(
    "context-balance",
    version="0.1.0",
    description=(
        "Detects pruning-retrieval feedback loops in LLM agent context management. "
        "Tracks retrieval and pruning events, detects oscillation patterns and "
        "re-retrieval waste, and correlates context changes with quality signals."
    ),
)

# Global state — initialized on first use
_store: EventStore | None = None
_session_id: str = ""


def _get_store() -> EventStore:
    global _store
    if _store is None:
        _store = EventStore()
    return _store


def _get_session_id() -> str:
    global _session_id
    if not _session_id:
        _session_id = uuid.uuid4().hex[:12]
    return _session_id


# --- Instrumentation tools ---


@mcp.tool()
def log_retrieval(
    source: str,
    query: str,
    result_tokens: int,
    relevance_score: float | None = None,
) -> str:
    """Log a context retrieval event.

    Call this when the agent retrieves context from any source: RAG, file read,
    web fetch, memory recall, MCP resource load, etc.

    Args:
        source: Where the content was retrieved from (file path, URL, memory key, etc.)
        query: The query or intent that triggered the retrieval
        result_tokens: Approximate token count of the retrieved content
        relevance_score: Optional relevance score 0.0-1.0 if your system computes one
    """
    event_data = RetrievalEvent(
        source=source,
        query=query,
        result_tokens=result_tokens,
        relevance_score=relevance_score,
    )
    store = _get_store()
    stored = store.add_event(
        EventType.RETRIEVAL, _get_session_id(), event_data.model_dump()
    )
    return json.dumps(
        {
            "status": "logged",
            "event_id": stored.id,
            "sequence": stored.sequence,
            "type": "retrieval",
            "source": source,
            "tokens": result_tokens,
        }
    )


@mcp.tool()
def log_pruning(
    target: str,
    tokens_removed: int,
    reason: str,
    method: str = "other",
) -> str:
    """Log a context pruning event.

    Call this when context is removed: summarization, truncation, compression,
    explicit removal, conversation compaction, etc.

    Args:
        target: Description of what was pruned (e.g., "conversation turns 5-12")
        tokens_removed: Approximate tokens removed
        reason: Why the pruning happened (e.g., "staleness", "token limit", "manual")
        method: How it was performed — one of: summarize, truncate, drop, compress, other
    """
    try:
        pm = PruningMethod(method.lower())
    except ValueError:
        pm = PruningMethod.OTHER

    event_data = PruningEvent(
        target=target,
        tokens_removed=tokens_removed,
        reason=reason,
        method=pm,
    )
    store = _get_store()
    stored = store.add_event(
        EventType.PRUNING, _get_session_id(), event_data.model_dump()
    )
    return json.dumps(
        {
            "status": "logged",
            "event_id": stored.id,
            "sequence": stored.sequence,
            "type": "pruning",
            "target": target,
            "tokens_removed": tokens_removed,
        }
    )


@mcp.tool()
def log_quality_signal(
    metric: str,
    value: float,
    context_size: int | None = None,
) -> str:
    """Log a quality measurement signal.

    Call this when there's a quality signal: eval score, user feedback, task
    success/failure, error, hallucination detection, etc. Used to correlate
    context changes with quality outcomes.

    Args:
        metric: Name of the quality metric (e.g., "task_success", "eval_score", "error")
        value: The metric value (0.0-1.0 scale preferred; for binary, use 0.0=fail 1.0=pass)
        context_size: Optional approximate context size in tokens at time of measurement
    """
    event_data = QualityEvent(
        metric=metric,
        value=value,
        context_size=context_size,
    )
    store = _get_store()
    stored = store.add_event(
        EventType.QUALITY, _get_session_id(), event_data.model_dump()
    )
    return json.dumps(
        {
            "status": "logged",
            "event_id": stored.id,
            "sequence": stored.sequence,
            "type": "quality",
            "metric": metric,
            "value": value,
        }
    )


# --- Query tools ---


@mcp.tool()
def get_balance_report(window: int | None = None) -> str:
    """Get a balance analysis report for the current session.

    Analyzes retrieval and pruning patterns, detects oscillation cycles and
    re-retrieval waste, and correlates context changes with quality signals.

    Args:
        window: Optional — only analyze the last N events. Omit for full session.

    Returns:
        JSON report with status, cycle count, re-retrievals, regret events,
        and a recommendation.
    """
    store = _get_store()
    session_id = _get_session_id()
    events = store.get_events(session_id, last_n=window)

    if not events:
        return json.dumps(
            {
                "status": "no_data",
                "message": "No events logged for this session yet. "
                "Use log_retrieval, log_pruning, and log_quality_signal "
                "to instrument your agent.",
            }
        )

    report = build_report(events, session_id)
    return report.model_dump_json(indent=2)


@mcp.tool()
def get_event_timeline(last_n: int = 50) -> str:
    """Get the raw event timeline for debugging.

    Args:
        last_n: Number of most recent events to return (default 50).

    Returns:
        JSON array of events with type, timestamp, sequence, and data.
    """
    store = _get_store()
    events = store.get_events(_get_session_id(), last_n=last_n)
    timeline = [
        {
            "seq": ev.sequence,
            "type": ev.event_type.value,
            "ts": ev.timestamp.isoformat(),
            "data": ev.data,
        }
        for ev in events
    ]
    return json.dumps(timeline, indent=2)


@mcp.tool()
def get_context_size_curve(last_n: int = 100) -> str:
    """Get the context size over time as a series of data points.

    Shows how the cumulative context size (retrievals minus pruning) changes
    over the session. Useful for visualizing oscillation patterns.

    Args:
        last_n: Number of most recent context-changing events to include (default 100).

    Returns:
        JSON with data points and an ASCII sparkline visualization.
    """
    store = _get_store()
    events = store.get_events(_get_session_id(), last_n=last_n)

    points: list[dict[str, Any]] = []
    cumulative = 0
    for ev in events:
        if ev.event_type == EventType.RETRIEVAL:
            cumulative += ev.data.get("result_tokens", 0)
            points.append(
                {"seq": ev.sequence, "size": cumulative, "event": "retrieval"}
            )
        elif ev.event_type == EventType.PRUNING:
            cumulative -= ev.data.get("tokens_removed", 0)
            cumulative = max(cumulative, 0)
            points.append(
                {"seq": ev.sequence, "size": cumulative, "event": "pruning"}
            )

    if not points:
        return json.dumps({"points": [], "sparkline": "(no data)"})

    # Build ASCII sparkline
    max_size = max(p["size"] for p in points) or 1
    sparkline_chars = "▁▂▃▄▅▆▇█"
    sparkline = ""
    for p in points[-60:]:  # last 60 points for readability
        idx = min(int((p["size"] / max_size) * (len(sparkline_chars) - 1)), len(sparkline_chars) - 1)
        sparkline += sparkline_chars[idx]

    return json.dumps(
        {
            "points": points,
            "sparkline": sparkline,
            "max_tokens": max_size,
            "current_tokens": points[-1]["size"] if points else 0,
        },
        indent=2,
    )


def main():
    """Run the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
