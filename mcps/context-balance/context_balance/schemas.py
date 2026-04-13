"""Pydantic models for context-balance events and reports."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    RETRIEVAL = "retrieval"
    PRUNING = "pruning"
    QUALITY = "quality"


class PruningMethod(str, Enum):
    SUMMARIZE = "summarize"
    TRUNCATE = "truncate"
    DROP = "drop"
    COMPRESS = "compress"
    OTHER = "other"


class RetrievalEvent(BaseModel):
    source: str = Field(description="Where the content was retrieved from (file path, URL, memory key, MCP resource, etc.)")
    query: str = Field(description="The query or intent that triggered the retrieval")
    result_tokens: int = Field(description="Approximate token count of the retrieved content")
    relevance_score: Optional[float] = Field(default=None, description="Optional relevance score 0.0-1.0 if the system computes one")


class PruningEvent(BaseModel):
    target: str = Field(description="Description of what was pruned (e.g., 'conversation turns 5-12', 'tool output from turn 8')")
    tokens_removed: int = Field(description="Approximate tokens removed")
    reason: str = Field(description="Why the pruning happened (e.g., 'staleness', 'token limit', 'manual', 'automatic')")
    method: PruningMethod = Field(description="How the pruning was performed")


class QualityEvent(BaseModel):
    metric: str = Field(description="Name of the quality metric (e.g., 'task_success', 'user_rating', 'eval_score', 'error')")
    value: float = Field(description="The metric value")
    context_size: Optional[int] = Field(default=None, description="Approximate context size in tokens at time of measurement")


class StoredEvent(BaseModel):
    id: int
    event_type: EventType
    timestamp: datetime
    session_id: str
    sequence: int
    data: dict


class ReRetrievalRecord(BaseModel):
    source: str
    times_retrieved: int
    times_pruned: int
    total_wasted_tokens: int
    first_seen_seq: int
    last_seen_seq: int


class BalanceStatus(str, Enum):
    HEALTHY = "healthy"
    MODERATE = "moderate"
    OSCILLATING = "oscillating"
    CRITICAL = "critical"


class BalanceReport(BaseModel):
    status: BalanceStatus
    session_id: str
    total_events: int
    total_retrievals: int
    total_prunes: int
    total_quality_signals: int
    net_context_tokens: int = Field(description="Running sum: total retrieved - total pruned")
    cycles_detected: int = Field(description="Number of grow/shrink oscillation cycles")
    avg_cycle_period: Optional[float] = Field(default=None, description="Average events between oscillation peaks")
    re_retrievals: list[ReRetrievalRecord] = Field(default_factory=list)
    prune_regret_events: int = Field(description="Quality drops within 5 events after a prune")
    retrieval_regret_events: int = Field(description="Quality drops within 5 events after a retrieval")
    recommendation: str
