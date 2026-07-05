"""Replay a scripted synthetic agent session through the real storage and
detection layers and print the resulting balance report.

The script simulates a RAG agent that falls into the pruning-retrieval
feedback loop: it over-retrieves, hits its token budget, summarizes away the
docs it still needs, then re-retrieves them to compensate. Quality drops
follow the prunes.

Run from mcps/context-balance:

    python examples/synthetic_session.py
"""

import tempfile
from pathlib import Path

from context_balance.detection import build_report
from context_balance.schemas import EventType
from context_balance.storage import EventStore

SESSION = "synthetic-loop-demo"

# (tool, kwargs) in the order the agent would emit them over ~25 turns
SCRIPT = [
    # Turn 1-4: initial research burst, reasonable retrievals
    ("retrieval", {"source": "kb/product_docs", "query": "return policy", "result_tokens": 2400, "relevance_score": 0.82}),
    ("retrieval", {"source": "kb/pricing", "query": "enterprise tier pricing", "result_tokens": 1800, "relevance_score": 0.77}),
    ("retrieval", {"source": "crm/account_history", "query": "customer prior tickets", "result_tokens": 3100, "relevance_score": 0.64}),
    ("quality", {"metric": "task_success", "value": 1.0, "context_size": 9800}),
    # Turn 5-8: keeps retrieving, window bloats
    ("retrieval", {"source": "kb/legal_terms", "query": "refund exceptions", "result_tokens": 4200, "relevance_score": 0.41}),
    ("retrieval", {"source": "web/competitor_pricing", "query": "competitor refund policy", "result_tokens": 3600, "relevance_score": 0.35}),
    ("quality", {"metric": "eval_score", "value": 0.7, "context_size": 17600}),
    # Turn 9: token limit pressure, aggressive summarization drops signal
    ("pruning", {"target": "kb/product_docs", "tokens_removed": 2400, "reason": "token limit approaching", "method": "summarize"}),
    ("pruning", {"target": "kb/pricing", "tokens_removed": 1800, "reason": "token limit approaching", "method": "summarize"}),
    # Turn 10-11: quality craters, the summary lost the exact policy text
    ("quality", {"metric": "eval_score", "value": 0.3, "context_size": 13400}),
    # Turn 12-13: agent re-retrieves what was just pruned
    ("retrieval", {"source": "kb/product_docs", "query": "return policy exact wording", "result_tokens": 2600, "relevance_score": 0.85}),
    ("retrieval", {"source": "kb/pricing", "query": "enterprise tier pricing table", "result_tokens": 1900, "relevance_score": 0.80}),
    ("quality", {"metric": "task_success", "value": 1.0, "context_size": 17900}),
    # Turn 14-17: second bloat wave
    ("retrieval", {"source": "web/industry_regulations", "query": "consumer protection rules", "result_tokens": 5200, "relevance_score": 0.30}),
    ("quality", {"metric": "eval_score", "value": 0.6, "context_size": 23100}),
    # Turn 18: prunes again, takes product_docs with it again
    ("pruning", {"target": "kb/product_docs", "tokens_removed": 2600, "reason": "token limit approaching", "method": "truncate"}),
    ("pruning", {"target": "web/competitor_pricing", "tokens_removed": 3600, "reason": "staleness", "method": "drop"}),
    ("quality", {"metric": "error", "value": 0.0, "context_size": 16900}),
    # Turn 20-21: third retrieval of the same source
    ("retrieval", {"source": "kb/product_docs", "query": "return policy", "result_tokens": 2500, "relevance_score": 0.84}),
    ("quality", {"metric": "task_success", "value": 1.0, "context_size": 19400}),
    # Turn 22-25: cycle continues
    ("retrieval", {"source": "crm/account_history", "query": "escalation notes", "result_tokens": 2800, "relevance_score": 0.55}),
    ("pruning", {"target": "web/industry_regulations", "tokens_removed": 5200, "reason": "irrelevant", "method": "drop"}),
    ("retrieval", {"source": "kb/legal_terms", "query": "refund exceptions", "result_tokens": 4100, "relevance_score": 0.45}),
    ("quality", {"metric": "eval_score", "value": 0.5, "context_size": 21200}),
]

EVENT_TYPES = {
    "retrieval": EventType.RETRIEVAL,
    "pruning": EventType.PRUNING,
    "quality": EventType.QUALITY,
}


def main() -> None:
    db_path = Path(tempfile.mkdtemp()) / "events.db"
    store = EventStore(str(db_path))

    for tool, data in SCRIPT:
        store.add_event(EVENT_TYPES[tool], SESSION, data)

    events = store.get_events(SESSION)
    report = build_report(events, SESSION)
    print(report.model_dump_json(indent=2))
    store.close()


if __name__ == "__main__":
    main()
