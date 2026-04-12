import { useState, useCallback, useEffect, useRef } from "react";

const QUADRANTS = {
  open: {
    label: "OPEN",
    subtitle: "Aligned",
    color: "#22c55e",
    bgColor: "rgba(34,197,94,0.06)",
    borderColor: "rgba(34,197,94,0.25)",
    icon: "◉",
    mechanism: "Goal State",
    description: "Agent surfaces it. Operator sees it.",
    examples: [
      "Traced tool invocations with I/O logging",
      "Explicit reasoning steps in structured output",
      "Declared confidence / uncertainty scores",
      "Version-pinned prompts tied to decisions",
    ],
  },
  blind: {
    label: "BLIND SPOT",
    subtitle: "Drift",
    color: "#f59e0b",
    bgColor: "rgba(245,158,11,0.06)",
    borderColor: "rgba(245,158,11,0.25)",
    icon: "◐",
    mechanism: "Feedback",
    description: "Operator detects it. Agent can't self-assess.",
    examples: [
      "Gradual output quality degradation",
      "Systematic bias in tool selection",
      "Latent prompt injection vulnerabilities",
      "Performance patterns tied to external state",
    ],
  },
  hidden: {
    label: "HIDDEN",
    subtitle: "Opaque",
    color: "#ef4444",
    bgColor: "rgba(239,68,68,0.06)",
    borderColor: "rgba(239,68,68,0.25)",
    icon: "◑",
    mechanism: "Disclosure",
    description: "Agent 'has' it. Operator can't see it.",
    examples: [
      "Implicit assumptions from retrieved docs",
      "Silent step-skipping in workflows",
      "Context window state with no external signal",
      "Inter-agent comms dropping critical context",
    ],
  },
  unknown: {
    label: "UNKNOWN",
    subtitle: "Emergent",
    color: "#8b5cf6",
    bgColor: "rgba(139,92,246,0.06)",
    borderColor: "rgba(139,92,246,0.25)",
    icon: "○",
    mechanism: "Exploration",
    description: "Neither agent nor operator can identify it.",
    examples: [
      "Multi-turn escalation attacks",
      "Emergent multi-agent coordination",
      "Novel tool misuse patterns",
      "Compounding cross-boundary errors",
    ],
  },
};

const DIAGNOSTIC_QUESTIONS = [
  {
    id: "tracing",
    text: "Are all tool calls and their inputs/outputs logged in structured traces?",
    quadrant: "open",
    weight: 2,
  },
  {
    id: "reasoning",
    text: "Does the agent produce structured chain-of-thought or reasoning traces?",
    quadrant: "open",
    weight: 2,
  },
  {
    id: "confidence",
    text: "Does the agent declare confidence levels or uncertainty?",
    quadrant: "open",
    weight: 1,
  },
  {
    id: "versioning",
    text: "Are prompts, model versions, and configs tied to each decision?",
    quadrant: "open",
    weight: 1,
  },
  {
    id: "evals",
    text: "Do you run eval pipelines or LLM-as-judge on agent outputs?",
    quadrant: "blind",
    weight: 2,
  },
  {
    id: "drift",
    text: "Do you monitor for behavioral drift over time (output quality, tool selection patterns)?",
    quadrant: "blind",
    weight: 2,
  },
  {
    id: "anomaly",
    text: "Do you have anomaly detection on agent behavior metrics?",
    quadrant: "blind",
    weight: 1,
  },
  {
    id: "human_review",
    text: "Is there a human review loop for a sample of agent decisions?",
    quadrant: "blind",
    weight: 1,
  },
  {
    id: "context_provenance",
    text: "Can you trace which retrieved documents influenced a specific decision?",
    quadrant: "hidden",
    weight: 2,
  },
  {
    id: "step_audit",
    text: "Would you know if the agent silently skipped a step in a multi-step workflow?",
    quadrant: "hidden",
    weight: 2,
  },
  {
    id: "inter_agent",
    text: "In multi-agent setups, do you audit what context is passed vs. dropped at handoffs?",
    quadrant: "hidden",
    weight: 1,
  },
  {
    id: "near_miss",
    text: "Can you detect 'near-miss' decisions where the agent almost took a harmful action?",
    quadrant: "hidden",
    weight: 1,
  },
  {
    id: "red_team",
    text: "Do you conduct adversarial testing or red-teaming against agent workflows?",
    quadrant: "unknown",
    weight: 2,
  },
  {
    id: "chaos",
    text: "Do you test agent behavior under degraded conditions (stale data, API failures)?",
    quadrant: "unknown",
    weight: 2,
  },
  {
    id: "multi_agent_emergent",
    text: "In multi-agent systems, do you test for emergent coordination or feedback loops?",
    quadrant: "unknown",
    weight: 1,
  },
  {
    id: "fail_safe",
    text: "Are there circuit breakers or safe-failure modes for unexpected agent behavior?",
    quadrant: "unknown",
    weight: 1,
  },
];

const VIEWS = { FRAMEWORK: 0, DIAGNOSTIC: 1, RESULTS: 2, ITEMS: 3 };

function QuadrantCard({ qKey, data, isSelected, onClick, itemCount, score }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: isSelected ? data.bgColor : "rgba(255,255,255,0.02)",
        border: `1px solid ${isSelected ? data.borderColor : "rgba(255,255,255,0.08)"}`,
        borderRadius: 12,
        padding: "20px 18px",
        cursor: "pointer",
        transition: "all 0.3s ease",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
        <div>
          <span style={{ fontSize: 20, marginRight: 8 }}>{data.icon}</span>
          <span style={{ color: data.color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 14, letterSpacing: "0.05em" }}>
            {data.label}
          </span>
        </div>
        {score !== undefined && (
          <div style={{
            background: `${data.color}20`,
            color: data.color,
            padding: "2px 10px",
            borderRadius: 20,
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 600,
          }}>
            {score}%
          </div>
        )}
      </div>
      <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", marginBottom: 8, letterSpacing: "0.08em" }}>
        {data.subtitle} · {data.mechanism}
      </div>
      <div style={{ color: "rgba(255,255,255,0.65)", fontSize: 13, lineHeight: 1.5 }}>
        {data.description}
      </div>
      {itemCount > 0 && (
        <div style={{ marginTop: 10, color: data.color, fontSize: 12, fontWeight: 600 }}>
          {itemCount} observation{itemCount !== 1 ? "s" : ""} logged
        </div>
      )}
    </div>
  );
}

function DiagnosticQuestion({ q, answer, onAnswer }) {
  const data = QUADRANTS[q.quadrant];
  return (
    <div style={{ marginBottom: 16, padding: "16px 18px", background: "rgba(255,255,255,0.02)", borderRadius: 10, border: "1px solid rgba(255,255,255,0.06)" }}>
      <div style={{ color: "rgba(255,255,255,0.85)", fontSize: 14, lineHeight: 1.5, marginBottom: 12 }}>
        {q.text}
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        {["yes", "partial", "no"].map((opt) => (
          <button
            key={opt}
            onClick={() => onAnswer(q.id, opt)}
            style={{
              padding: "6px 16px",
              borderRadius: 6,
              border: `1px solid ${answer === opt ? data.color : "rgba(255,255,255,0.12)"}`,
              background: answer === opt ? `${data.color}18` : "transparent",
              color: answer === opt ? data.color : "rgba(255,255,255,0.5)",
              fontSize: 12,
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s ease",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            {opt}
          </button>
        ))}
        <span style={{ marginLeft: 8, color: data.color, fontSize: 10, fontFamily: "'JetBrains Mono', monospace", opacity: 0.6 }}>
          {data.label}
        </span>
      </div>
    </div>
  );
}

function ScoreBar({ label, color, score, maxScore }) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0;
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <span style={{ color, fontSize: 12, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>{label}</span>
        <span style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>{pct}%</span>
      </div>
      <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 3, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

export default function AgenticJohariWindow() {
  const [view, setView] = useState(VIEWS.FRAMEWORK);
  const [selectedQuadrant, setSelectedQuadrant] = useState(null);
  const [answers, setAnswers] = useState({});
  const [items, setItems] = useState({ open: [], blind: [], hidden: [], unknown: [] });
  const [newItem, setNewItem] = useState("");
  const [addingTo, setAddingTo] = useState(null);

  const handleAnswer = useCallback((id, val) => {
    setAnswers((prev) => ({ ...prev, [id]: val }));
  }, []);

  const computeScores = useCallback(() => {
    const scores = {};
    Object.keys(QUADRANTS).forEach((qKey) => {
      const qs = DIAGNOSTIC_QUESTIONS.filter((q) => q.quadrant === qKey);
      const maxScore = qs.reduce((s, q) => s + q.weight, 0);
      const actual = qs.reduce((s, q) => {
        const a = answers[q.id];
        if (a === "yes") return s + q.weight;
        if (a === "partial") return s + q.weight * 0.5;
        return s;
      }, 0);
      scores[qKey] = { score: actual, max: maxScore, pct: maxScore > 0 ? Math.round((actual / maxScore) * 100) : 0 };
    });
    return scores;
  }, [answers]);

  const addItem = useCallback((quadrant) => {
    if (!newItem.trim()) return;
    setItems((prev) => ({
      ...prev,
      [quadrant]: [...prev[quadrant], { text: newItem.trim(), ts: Date.now() }],
    }));
    setNewItem("");
    setAddingTo(null);
  }, [newItem]);

  const removeItem = useCallback((quadrant, idx) => {
    setItems((prev) => ({
      ...prev,
      [quadrant]: prev[quadrant].filter((_, i) => i !== idx),
    }));
  }, []);

  const scores = computeScores();
  const totalAnswered = Object.keys(answers).length;
  const totalQuestions = DIAGNOSTIC_QUESTIONS.length;
  const overallScore = Object.values(scores).reduce((s, v) => s + v.pct, 0) / 4;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#0a0a0f",
      color: "#fff",
      fontFamily: "'Inter', -apple-system, sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700;900&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ padding: "32px 24px 0", maxWidth: 900, margin: "0 auto" }}>
        <div style={{ marginBottom: 4 }}>
          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "rgba(255,255,255,0.3)", letterSpacing: "0.15em", textTransform: "uppercase" }}>
            Framework v0.1
          </span>
        </div>
        <h1 style={{
          fontFamily: "'Playfair Display', serif",
          fontSize: 32,
          fontWeight: 900,
          margin: "0 0 6px 0",
          background: "linear-gradient(135deg, #22c55e, #f59e0b, #ef4444, #8b5cf6)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          lineHeight: 1.1,
        }}>
          The Agentic Johari Window
        </h1>
        <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 14, margin: "0 0 20px 0", lineHeight: 1.5 }}>
          Map what your AI agents know, hide, and can't see.
        </p>

        {/* Nav */}
        <div style={{ display: "flex", gap: 4, marginBottom: 24, flexWrap: "wrap" }}>
          {[
            { v: VIEWS.FRAMEWORK, label: "Framework" },
            { v: VIEWS.DIAGNOSTIC, label: "Diagnostic" },
            { v: VIEWS.RESULTS, label: `Results${totalAnswered > 0 ? ` (${Math.round(overallScore)}%)` : ""}` },
            { v: VIEWS.ITEMS, label: `Observations (${Object.values(items).flat().length})` },
          ].map(({ v, label }) => (
            <button
              key={v}
              onClick={() => setView(v)}
              style={{
                padding: "8px 14px",
                borderRadius: 6,
                border: "none",
                background: view === v ? "rgba(255,255,255,0.1)" : "transparent",
                color: view === v ? "#fff" : "rgba(255,255,255,0.4)",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "0 24px 48px", maxWidth: 900, margin: "0 auto" }}>

        {/* FRAMEWORK VIEW */}
        {view === VIEWS.FRAMEWORK && (
          <div>
            {/* 2x2 Grid */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 24 }}>
              {/* Axis labels */}
              <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "center", marginBottom: -4 }}>
                <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: "rgba(255,255,255,0.25)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  Operator Visible ← → Operator Not Visible
                </span>
              </div>
              {Object.entries(QUADRANTS).map(([key, data]) => (
                <QuadrantCard
                  key={key}
                  qKey={key}
                  data={data}
                  isSelected={selectedQuadrant === key}
                  onClick={() => setSelectedQuadrant(selectedQuadrant === key ? null : key)}
                  itemCount={items[key].length}
                />
              ))}
              <div style={{ gridColumn: "1 / -1", display: "flex", justifyContent: "center", marginTop: -4 }}>
                <span style={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: "rgba(255,255,255,0.25)", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  Agent Surfaces ↑ · Agent Doesn't ↓
                </span>
              </div>
            </div>

            {/* Expanded detail */}
            {selectedQuadrant && (
              <div style={{
                background: QUADRANTS[selectedQuadrant].bgColor,
                border: `1px solid ${QUADRANTS[selectedQuadrant].borderColor}`,
                borderRadius: 12,
                padding: 20,
                marginBottom: 24,
              }}>
                <div style={{ color: QUADRANTS[selectedQuadrant].color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13, marginBottom: 12 }}>
                  {QUADRANTS[selectedQuadrant].icon} {QUADRANTS[selectedQuadrant].label} — Expand via {QUADRANTS[selectedQuadrant].mechanism}
                </div>
                <div style={{ color: "rgba(255,255,255,0.7)", fontSize: 13, lineHeight: 1.6 }}>
                  {QUADRANTS[selectedQuadrant].examples.map((ex, i) => (
                    <div key={i} style={{ marginBottom: 6, paddingLeft: 16, position: "relative" }}>
                      <span style={{ position: "absolute", left: 0, color: QUADRANTS[selectedQuadrant].color, opacity: 0.5 }}>→</span>
                      {ex}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Dynamics */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: 20 }}>
              <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "rgba(255,255,255,0.4)", marginBottom: 14, letterSpacing: "0.08em" }}>
                EXPANSION MECHANISMS
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
                {[
                  { label: "Feedback", target: "Blind Spot", color: "#f59e0b", desc: "Evals, monitoring, human review" },
                  { label: "Disclosure", target: "Hidden", color: "#ef4444", desc: "Structured CoT, context provenance" },
                  { label: "Exploration", target: "Unknown", color: "#8b5cf6", desc: "Red-teaming, chaos engineering" },
                ].map((m) => (
                  <div key={m.label} style={{ textAlign: "center" }}>
                    <div style={{ color: m.color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13, marginBottom: 4 }}>
                      {m.label}
                    </div>
                    <div style={{ color: "rgba(255,255,255,0.3)", fontSize: 11, marginBottom: 4 }}>
                      shrinks {m.target}
                    </div>
                    <div style={{ color: "rgba(255,255,255,0.5)", fontSize: 11 }}>
                      {m.desc}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* DIAGNOSTIC VIEW */}
        {view === VIEWS.DIAGNOSTIC && (
          <div>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginBottom: 20, lineHeight: 1.5 }}>
              Answer these {totalQuestions} questions to assess your agent system's coverage across all four quadrants.
              <span style={{ color: "rgba(255,255,255,0.3)", marginLeft: 8 }}>
                {totalAnswered}/{totalQuestions} answered
              </span>
            </p>
            {Object.keys(QUADRANTS).map((qKey) => {
              const qs = DIAGNOSTIC_QUESTIONS.filter((q) => q.quadrant === qKey);
              return (
                <div key={qKey} style={{ marginBottom: 28 }}>
                  <div style={{
                    color: QUADRANTS[qKey].color,
                    fontFamily: "'JetBrains Mono', monospace",
                    fontWeight: 700,
                    fontSize: 12,
                    marginBottom: 10,
                    letterSpacing: "0.08em",
                  }}>
                    {QUADRANTS[qKey].icon} {QUADRANTS[qKey].label} COVERAGE
                  </div>
                  {qs.map((q) => (
                    <DiagnosticQuestion key={q.id} q={q} answer={answers[q.id]} onAnswer={handleAnswer} />
                  ))}
                </div>
              );
            })}
            {totalAnswered > 0 && (
              <button
                onClick={() => setView(VIEWS.RESULTS)}
                style={{
                  width: "100%",
                  padding: "14px",
                  borderRadius: 8,
                  border: "1px solid rgba(34,197,94,0.4)",
                  background: "rgba(34,197,94,0.1)",
                  color: "#22c55e",
                  fontSize: 14,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "'JetBrains Mono', monospace",
                }}
              >
                View Results →
              </button>
            )}
          </div>
        )}

        {/* RESULTS VIEW */}
        {view === VIEWS.RESULTS && (
          <div>
            {totalAnswered === 0 ? (
              <div style={{ textAlign: "center", padding: 40, color: "rgba(255,255,255,0.3)" }}>
                <div style={{ fontSize: 14, marginBottom: 12 }}>No diagnostic answers yet.</div>
                <button
                  onClick={() => setView(VIEWS.DIAGNOSTIC)}
                  style={{
                    padding: "10px 20px",
                    borderRadius: 6,
                    border: "1px solid rgba(255,255,255,0.15)",
                    background: "transparent",
                    color: "rgba(255,255,255,0.6)",
                    fontSize: 13,
                    cursor: "pointer",
                  }}
                >
                  Start Diagnostic
                </button>
              </div>
            ) : (
              <>
                {/* Overall score */}
                <div style={{
                  textAlign: "center",
                  padding: "28px 20px",
                  background: "rgba(255,255,255,0.02)",
                  borderRadius: 12,
                  border: "1px solid rgba(255,255,255,0.06)",
                  marginBottom: 24,
                }}>
                  <div style={{
                    fontSize: 56,
                    fontFamily: "'Playfair Display', serif",
                    fontWeight: 900,
                    background: overallScore >= 70 ? "linear-gradient(135deg, #22c55e, #4ade80)"
                      : overallScore >= 40 ? "linear-gradient(135deg, #f59e0b, #fbbf24)"
                      : "linear-gradient(135deg, #ef4444, #f87171)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                  }}>
                    {Math.round(overallScore)}%
                  </div>
                  <div style={{ color: "rgba(255,255,255,0.4)", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                    OVERALL QUADRANT COVERAGE
                  </div>
                </div>

                {/* Per-quadrant bars */}
                <div style={{ marginBottom: 24 }}>
                  {Object.entries(QUADRANTS).map(([key, data]) => (
                    <ScoreBar key={key} label={data.label} color={data.color} score={scores[key].score} maxScore={scores[key].max} />
                  ))}
                </div>

                {/* Weakest quadrant callout */}
                {(() => {
                  const weakest = Object.entries(scores).sort((a, b) => a[1].pct - b[1].pct)[0];
                  const wData = QUADRANTS[weakest[0]];
                  return (
                    <div style={{
                      background: wData.bgColor,
                      border: `1px solid ${wData.borderColor}`,
                      borderRadius: 12,
                      padding: 20,
                    }}>
                      <div style={{ color: wData.color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
                        ⚠ LARGEST GAP: {wData.label} ({weakest[1].pct}%)
                      </div>
                      <div style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, lineHeight: 1.5 }}>
                        Your agent system has the weakest coverage in the <strong style={{ color: wData.color }}>{wData.label}</strong> quadrant.
                        Expand this through <strong style={{ color: wData.color }}>{wData.mechanism}</strong> mechanisms:
                      </div>
                      <div style={{ marginTop: 10 }}>
                        {wData.examples.slice(0, 2).map((ex, i) => (
                          <div key={i} style={{ color: "rgba(255,255,255,0.5)", fontSize: 12, marginBottom: 4, paddingLeft: 16, position: "relative" }}>
                            <span style={{ position: "absolute", left: 0, color: wData.color }}>→</span>
                            {ex}
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </>
            )}
          </div>
        )}

        {/* OBSERVATIONS VIEW */}
        {view === VIEWS.ITEMS && (
          <div>
            <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 13, marginBottom: 20, lineHeight: 1.5 }}>
              Log specific observations about your agent system into each quadrant. Use this as a living diagnostic during development and review.
            </p>
            {Object.entries(QUADRANTS).map(([key, data]) => (
              <div key={key} style={{ marginBottom: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                  <span style={{ color: data.color, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, fontSize: 12, letterSpacing: "0.08em" }}>
                    {data.icon} {data.label}
                  </span>
                  <button
                    onClick={() => setAddingTo(addingTo === key ? null : key)}
                    style={{
                      padding: "4px 12px",
                      borderRadius: 4,
                      border: `1px solid ${addingTo === key ? data.color : "rgba(255,255,255,0.1)"}`,
                      background: "transparent",
                      color: addingTo === key ? data.color : "rgba(255,255,255,0.4)",
                      fontSize: 11,
                      cursor: "pointer",
                      fontFamily: "'JetBrains Mono', monospace",
                    }}
                  >
                    + Add
                  </button>
                </div>

                {addingTo === key && (
                  <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                    <input
                      value={newItem}
                      onChange={(e) => setNewItem(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && addItem(key)}
                      placeholder="Describe the observation..."
                      style={{
                        flex: 1,
                        padding: "8px 12px",
                        borderRadius: 6,
                        border: `1px solid ${data.borderColor}`,
                        background: "rgba(0,0,0,0.3)",
                        color: "#fff",
                        fontSize: 13,
                        outline: "none",
                      }}
                      autoFocus
                    />
                    <button
                      onClick={() => addItem(key)}
                      style={{
                        padding: "8px 16px",
                        borderRadius: 6,
                        border: "none",
                        background: data.color,
                        color: "#000",
                        fontSize: 12,
                        fontWeight: 700,
                        cursor: "pointer",
                      }}
                    >
                      Save
                    </button>
                  </div>
                )}

                {items[key].length === 0 ? (
                  <div style={{ color: "rgba(255,255,255,0.15)", fontSize: 12, fontStyle: "italic", padding: "8px 0" }}>
                    No observations yet
                  </div>
                ) : (
                  items[key].map((item, idx) => (
                    <div key={idx} style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "10px 14px",
                      background: "rgba(255,255,255,0.02)",
                      borderRadius: 8,
                      border: "1px solid rgba(255,255,255,0.05)",
                      marginBottom: 6,
                    }}>
                      <span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13 }}>{item.text}</span>
                      <button
                        onClick={() => removeItem(key, idx)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "rgba(255,255,255,0.2)",
                          cursor: "pointer",
                          fontSize: 16,
                          padding: "0 4px",
                          flexShrink: 0,
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
