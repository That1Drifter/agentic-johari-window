"""Detection algorithms for context-balance feedback loops."""

from .schemas import (
    BalanceReport,
    BalanceStatus,
    EventType,
    ReRetrievalRecord,
    StoredEvent,
)


def _normalize_source(source: str) -> str:
    """Normalize a source string for comparison."""
    return source.strip().lower().replace("\\", "/")


def detect_oscillation(
    events: list[StoredEvent],
    min_amplitude: int = 1000,
) -> tuple[int, float | None]:
    """Detect grow/shrink oscillation cycles in context size.

    Returns (cycles_detected, avg_cycle_period).
    A cycle is: context grows past a peak, shrinks past a trough, grows again.
    """
    if not events:
        return 0, None

    # Build context-size curve from retrieval (+) and pruning (-) events
    size_deltas: list[tuple[int, int]] = []  # (sequence, cumulative_size)
    cumulative = 0
    for ev in events:
        if ev.event_type == EventType.RETRIEVAL:
            cumulative += ev.data.get("result_tokens", 0)
            size_deltas.append((ev.sequence, cumulative))
        elif ev.event_type == EventType.PRUNING:
            cumulative -= ev.data.get("tokens_removed", 0)
            size_deltas.append((ev.sequence, cumulative))

    if len(size_deltas) < 4:
        return 0, None

    # Find local peaks and troughs
    peaks = []
    troughs = []
    for i in range(1, len(size_deltas) - 1):
        prev_size = size_deltas[i - 1][1]
        curr_size = size_deltas[i][1]
        next_size = size_deltas[i + 1][1]
        if curr_size > prev_size and curr_size > next_size:
            peaks.append(size_deltas[i])
        elif curr_size < prev_size and curr_size < next_size:
            troughs.append(size_deltas[i])

    # Count cycles: peak → trough → peak with sufficient amplitude
    cycles = 0
    cycle_starts = []
    peak_idx = 0
    trough_idx = 0

    while peak_idx < len(peaks) and trough_idx < len(troughs):
        peak = peaks[peak_idx]
        # Find next trough after this peak
        while trough_idx < len(troughs) and troughs[trough_idx][0] < peak[0]:
            trough_idx += 1
        if trough_idx >= len(troughs):
            break
        trough = troughs[trough_idx]

        # Check amplitude
        amplitude = peak[1] - trough[1]
        if amplitude >= min_amplitude:
            cycles += 1
            cycle_starts.append(peak[0])

        peak_idx += 1

    # Average cycle period
    avg_period = None
    if len(cycle_starts) >= 2:
        gaps = [cycle_starts[i + 1] - cycle_starts[i] for i in range(len(cycle_starts) - 1)]
        avg_period = sum(gaps) / len(gaps)

    return cycles, avg_period


def detect_re_retrievals(events: list[StoredEvent]) -> list[ReRetrievalRecord]:
    """Detect content that was retrieved, pruned, then retrieved again."""
    # Track sources: source → list of (event_type, sequence, tokens)
    source_history: dict[str, list[tuple[EventType, int, int]]] = {}

    for ev in events:
        if ev.event_type == EventType.RETRIEVAL:
            key = _normalize_source(ev.data.get("source", ""))
            if not key:
                continue
            tokens = ev.data.get("result_tokens", 0)
            source_history.setdefault(key, []).append(
                (EventType.RETRIEVAL, ev.sequence, tokens)
            )
        elif ev.event_type == EventType.PRUNING:
            target = _normalize_source(ev.data.get("target", ""))
            if not target:
                continue
            tokens = ev.data.get("tokens_removed", 0)
            # Check if this prune target matches any known retrieval source
            for key in source_history:
                if key in target or target in key:
                    source_history[key].append(
                        (EventType.PRUNING, ev.sequence, tokens)
                    )
                    break

    # Find sources with retrieve → prune → retrieve pattern
    results = []
    for source, history in source_history.items():
        retrieval_count = sum(1 for t, _, _ in history if t == EventType.RETRIEVAL)
        prune_count = sum(1 for t, _, _ in history if t == EventType.PRUNING)

        if retrieval_count >= 2 and prune_count >= 1:
            # This is a re-retrieval
            total_tokens = sum(tokens for t, _, tokens in history if t == EventType.RETRIEVAL)
            sequences = [seq for _, seq, _ in history]
            results.append(
                ReRetrievalRecord(
                    source=source,
                    times_retrieved=retrieval_count,
                    times_pruned=prune_count,
                    total_wasted_tokens=total_tokens,
                    first_seen_seq=min(sequences),
                    last_seen_seq=max(sequences),
                )
            )

    results.sort(key=lambda r: r.total_wasted_tokens, reverse=True)
    return results


def detect_quality_correlation(
    events: list[StoredEvent],
    lookback: int = 5,
) -> tuple[int, int]:
    """Detect quality drops correlated with recent prunes or retrievals.

    Returns (prune_regret_count, retrieval_regret_count).
    """
    prune_regret = 0
    retrieval_regret = 0

    quality_events = [ev for ev in events if ev.event_type == EventType.QUALITY]

    for qev in quality_events:
        value = qev.data.get("value", 0)
        # A quality "drop" is a value < 0.5 on a 0-1 scale,
        # or the metric is explicitly named "error"
        is_negative = value < 0.5 or qev.data.get("metric", "").lower() in (
            "error",
            "failure",
            "hallucination",
        )
        if not is_negative:
            continue

        # Look back for recent prunes and retrievals
        recent = [
            ev
            for ev in events
            if ev.sequence < qev.sequence
            and ev.sequence >= qev.sequence - lookback
        ]
        recent_prunes = [ev for ev in recent if ev.event_type == EventType.PRUNING]
        recent_retrievals = [ev for ev in recent if ev.event_type == EventType.RETRIEVAL]

        if recent_prunes:
            prune_regret += 1
        if recent_retrievals:
            retrieval_regret += 1

    return prune_regret, retrieval_regret


def build_report(events: list[StoredEvent], session_id: str) -> BalanceReport:
    """Build a complete balance report from a session's events."""
    counts = {et: 0 for et in EventType}
    for ev in events:
        counts[ev.event_type] = counts.get(ev.event_type, 0) + 1

    # Net context size
    net_tokens = 0
    for ev in events:
        if ev.event_type == EventType.RETRIEVAL:
            net_tokens += ev.data.get("result_tokens", 0)
        elif ev.event_type == EventType.PRUNING:
            net_tokens -= ev.data.get("tokens_removed", 0)

    cycles, avg_period = detect_oscillation(events)
    re_retrievals = detect_re_retrievals(events)
    prune_regret, retrieval_regret = detect_quality_correlation(events)

    # Determine status
    if cycles >= 5 or len(re_retrievals) >= 3:
        status = BalanceStatus.CRITICAL
    elif cycles >= 3 or len(re_retrievals) >= 1:
        status = BalanceStatus.OSCILLATING
    elif cycles >= 1 or retrieval_regret >= 2 or prune_regret >= 2:
        status = BalanceStatus.MODERATE
    else:
        status = BalanceStatus.HEALTHY

    # Build recommendation
    if status == BalanceStatus.HEALTHY:
        recommendation = "Context balance is healthy. No feedback loop detected."
    elif status == BalanceStatus.MODERATE:
        if retrieval_regret > prune_regret:
            recommendation = (
                f"Moderate imbalance detected. {retrieval_regret} quality drops "
                f"correlated with retrievals vs {prune_regret} with prunes. "
                "Consider raising retrieval relevance threshold."
            )
        else:
            recommendation = (
                f"Moderate imbalance detected. {prune_regret} quality drops "
                f"correlated with prunes vs {retrieval_regret} with retrievals. "
                "Pruning may be too aggressive — signal is being lost."
            )
    elif status == BalanceStatus.OSCILLATING:
        parts = [f"Oscillating: {cycles} grow/shrink cycles detected."]
        if re_retrievals:
            rr = re_retrievals[0]
            parts.append(
                f"'{rr.source}' retrieved {rr.times_retrieved}x and pruned "
                f"{rr.times_pruned}x, wasting ~{rr.total_wasted_tokens} tokens."
            )
        parts.append(
            "System is in a prune-retrieve feedback loop. "
            "Pin critical context to prevent re-retrieval, or raise pruning staleness threshold."
        )
        recommendation = " ".join(parts)
    else:  # CRITICAL
        recommendation = (
            f"Critical: {cycles} oscillation cycles, "
            f"{len(re_retrievals)} re-retrieved sources. "
            "Context management is dysfunctional. Consider: "
            "(1) pinning essential context as non-prunable, "
            "(2) reducing retrieval top-K, "
            "(3) adding a relevance gate before retrieval."
        )

    return BalanceReport(
        status=status,
        session_id=session_id,
        total_events=len(events),
        total_retrievals=counts[EventType.RETRIEVAL],
        total_prunes=counts[EventType.PRUNING],
        total_quality_signals=counts[EventType.QUALITY],
        net_context_tokens=max(net_tokens, 0),
        cycles_detected=cycles,
        avg_cycle_period=avg_period,
        re_retrievals=re_retrievals[:10],
        prune_regret_events=prune_regret,
        retrieval_regret_events=retrieval_regret,
        recommendation=recommendation,
    )
