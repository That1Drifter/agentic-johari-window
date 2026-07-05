"""Unit tests for detection algorithms.

Synthetic event streams with known patterns, per the testing strategy in the
tools plan: verify detection fires on pathological patterns and stays quiet
on healthy ones.
"""

from datetime import datetime, timezone

from context_balance.detection import (
    build_report,
    detect_oscillation,
    detect_quality_correlation,
    detect_re_retrievals,
)
from context_balance.schemas import BalanceStatus, EventType, StoredEvent

_SEQ = 0


def _event(event_type: EventType, data: dict, sequence: int | None = None) -> StoredEvent:
    global _SEQ
    _SEQ += 1
    return StoredEvent(
        id=_SEQ,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        session_id="test-session",
        sequence=sequence if sequence is not None else _SEQ,
        data=data,
    )


def retrieval(source: str, tokens: int, seq: int) -> StoredEvent:
    return _event(
        EventType.RETRIEVAL,
        {"source": source, "query": "q", "result_tokens": tokens},
        sequence=seq,
    )


def pruning(target: str, tokens: int, seq: int) -> StoredEvent:
    return _event(
        EventType.PRUNING,
        {"target": target, "tokens_removed": tokens, "reason": "test", "method": "drop"},
        sequence=seq,
    )


def quality(value: float, seq: int, metric: str = "eval_score") -> StoredEvent:
    return _event(EventType.QUALITY, {"metric": metric, "value": value}, sequence=seq)


class TestDetectOscillation:
    def test_empty_events(self):
        assert detect_oscillation([]) == (0, None)

    def test_healthy_monotonic_growth_no_cycles(self):
        events = [retrieval(f"doc-{i}", 2000, seq=i) for i in range(1, 9)]
        cycles, _ = detect_oscillation(events)
        assert cycles == 0

    def test_single_prune_down_is_not_a_cycle(self):
        # Grow, prune once, stay down: deliberate cleanup, not oscillation.
        events = [
            retrieval("a", 5000, seq=1),
            retrieval("b", 5000, seq=2),
            pruning("a", 8000, seq=3),
            retrieval("c", 100, seq=4),  # tiny rebound below amplitude
            pruning("c", 100, seq=5),
        ]
        cycles, _ = detect_oscillation(events)
        assert cycles == 0

    def test_peak_trough_without_second_peak_is_not_a_cycle(self):
        # The docstring promises peak → trough → peak. A half-cycle
        # (peak → trough, then flatline/decline) must not count.
        events = [
            retrieval("a", 5000, seq=1),
            retrieval("b", 5000, seq=2),
            pruning("a", 6000, seq=3),
            pruning("b", 2000, seq=4),
            pruning("b", 1000, seq=5),
        ]
        cycles, _ = detect_oscillation(events)
        assert cycles == 0

    def test_full_cycle_detected(self):
        # grow → peak → prune → trough → grow → peak
        events = [
            retrieval("a", 3000, seq=1),
            retrieval("b", 3000, seq=2),   # peak at 6000
            pruning("a", 5000, seq=3),     # trough at 1000
            retrieval("a", 4000, seq=4),   # rebound to 5000 (peak)
            pruning("b", 3000, seq=5),     # tail so seq 4 is a local peak
        ]
        cycles, _ = detect_oscillation(events)
        assert cycles == 1

    def test_repeated_oscillation_counts_each_cycle(self):
        events = []
        seq = 0
        for _ in range(4):
            seq += 1
            events.append(retrieval("doc", 4000, seq=seq))
            seq += 1
            events.append(retrieval("doc2", 2000, seq=seq))
            seq += 1
            events.append(pruning("doc", 5500, seq=seq))
        cycles, avg_period = detect_oscillation(events)
        assert cycles == 3  # 4 peaks, 3 full peak→trough→peak cycles
        assert avg_period is not None

    def test_below_amplitude_ignored(self):
        events = [
            retrieval("a", 500, seq=1),
            retrieval("b", 400, seq=2),
            pruning("a", 600, seq=3),
            retrieval("a", 500, seq=4),
            pruning("b", 400, seq=5),
        ]
        cycles, _ = detect_oscillation(events, min_amplitude=1000)
        assert cycles == 0


class TestDetectReRetrievals:
    def test_no_events(self):
        assert detect_re_retrievals([]) == []

    def test_retrieve_prune_retrieve_flagged(self):
        events = [
            retrieval("docs/api.md", 2000, seq=1),
            pruning("docs/api.md", 2000, seq=2),
            retrieval("docs/api.md", 2100, seq=3),
        ]
        records = detect_re_retrievals(events)
        assert len(records) == 1
        rec = records[0]
        assert rec.source == "docs/api.md"
        assert rec.times_retrieved == 2
        assert rec.times_pruned == 1
        # Only the post-prune retrieval is waste; the first was legitimate.
        assert rec.total_wasted_tokens == 2100
        assert rec.first_seen_seq == 1
        assert rec.last_seen_seq == 3

    def test_retrieve_retrieve_prune_not_flagged(self):
        # Same counts as the pathological case, wrong order: no loop.
        events = [
            retrieval("docs/api.md", 2000, seq=1),
            retrieval("docs/api.md", 2100, seq=2),
            pruning("docs/api.md", 4100, seq=3),
        ]
        assert detect_re_retrievals(events) == []

    def test_repeated_loop_accumulates_waste(self):
        events = [
            retrieval("kb/policy", 1000, seq=1),
            pruning("kb/policy", 1000, seq=2),
            retrieval("kb/policy", 1200, seq=3),
            pruning("kb/policy", 1200, seq=4),
            retrieval("kb/policy", 1300, seq=5),
        ]
        records = detect_re_retrievals(events)
        assert len(records) == 1
        assert records[0].times_retrieved == 3
        assert records[0].times_pruned == 2
        assert records[0].total_wasted_tokens == 1200 + 1300

    def test_broad_prune_target_matches_all_sources(self):
        # One prune whose target substring-covers two sources must attach
        # to both, so a later re-retrieval of either is caught.
        events = [
            retrieval("docs", 1000, seq=1),
            retrieval("docs/api.md", 2000, seq=2),
            pruning("docs", 3000, seq=3),
            retrieval("docs/api.md", 2000, seq=4),
            retrieval("docs", 1000, seq=5),
        ]
        records = detect_re_retrievals(events)
        assert {r.source for r in records} == {"docs", "docs/api.md"}

    def test_unrelated_prune_does_not_flag(self):
        events = [
            retrieval("docs/api.md", 2000, seq=1),
            pruning("conversation turns 1-5", 3000, seq=2),
            retrieval("docs/api.md", 2000, seq=3),
        ]
        assert detect_re_retrievals(events) == []

    def test_sorted_by_wasted_tokens(self):
        events = [
            retrieval("small", 100, seq=1),
            pruning("small", 100, seq=2),
            retrieval("small", 100, seq=3),
            retrieval("big", 5000, seq=4),
            pruning("big", 5000, seq=5),
            retrieval("big", 5000, seq=6),
        ]
        records = detect_re_retrievals(events)
        assert [r.source for r in records] == ["big", "small"]


class TestDetectQualityCorrelation:
    def test_quality_drop_after_prune_counts_as_prune_regret(self):
        events = [
            pruning("docs", 3000, seq=1),
            quality(0.2, seq=2),
        ]
        prune_regret, retrieval_regret = detect_quality_correlation(events)
        assert prune_regret == 1
        assert retrieval_regret == 0

    def test_healthy_quality_not_counted(self):
        events = [
            pruning("docs", 3000, seq=1),
            retrieval("docs", 1000, seq=2),
            quality(0.9, seq=3),
        ]
        assert detect_quality_correlation(events) == (0, 0)

    def test_drop_outside_lookback_not_counted(self):
        events = [
            pruning("docs", 3000, seq=1),
            quality(0.1, seq=20),
        ]
        assert detect_quality_correlation(events) == (0, 0)


class TestBuildReport:
    def test_healthy_session_no_false_alarms(self):
        # Negative test from the plan: good retrieval, one deliberate prune,
        # good quality. Must report HEALTHY.
        events = [
            retrieval("docs/setup.md", 1500, seq=1),
            retrieval("docs/config.md", 1200, seq=2),
            quality(0.9, seq=3),
            pruning("conversation turns 1-3", 800, seq=4),
            retrieval("docs/deploy.md", 1400, seq=5),
            quality(0.95, seq=6),
        ]
        report = build_report(events, "healthy-session")
        assert report.status == BalanceStatus.HEALTHY
        assert report.cycles_detected == 0
        assert report.re_retrievals == []

    def test_feedback_loop_session_flags_oscillating_or_worse(self):
        # Pathological stream: same source retrieved/pruned repeatedly with
        # big swings, quality dropping after each prune.
        events = []
        seq = 0
        for _ in range(4):
            seq += 1
            events.append(retrieval("kb/main", 6000, seq=seq))
            seq += 1
            events.append(retrieval("kb/aux", 2000, seq=seq))
            seq += 1
            events.append(pruning("kb/main", 7000, seq=seq))
            seq += 1
            events.append(quality(0.3, seq=seq))
        report = build_report(events, "loop-session")
        assert report.status in (BalanceStatus.OSCILLATING, BalanceStatus.CRITICAL)
        assert report.cycles_detected >= 1
        assert any(r.source == "kb/main" for r in report.re_retrievals)

    def test_net_tokens_never_negative(self):
        events = [
            retrieval("a", 1000, seq=1),
            pruning("a", 5000, seq=2),
        ]
        report = build_report(events, "s")
        assert report.net_context_tokens == 0
