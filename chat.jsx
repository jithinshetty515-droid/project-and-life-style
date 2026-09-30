import React, { useEffect, useRef, useState } from "react";
import { Card, SourceBadge, ErrorBanner, Spinner } from "../components/ui.jsx";
import { api } from "../services/api.js";

const SUGGESTIONS = [
  "What should I focus on today?",
  "What if I study for my exam instead of my assignment?",
  "How should I plan tomorrow?",
  "Why am I falling behind?",
  "What patterns do you see in my routine?",
];

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: "twin",
      text: "I'm your Digital Twin. I answer using only the data you've allowed me to use. Ask me what to focus on, or ask a What-If question.",
      source: "rule_engine",
      factors: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    function handler(e) {
      if (e.detail) send(e.detail);
    }
    window.addEventListener("humantwin:ask", handler);
    return () => window.removeEventListener("humantwin:ask", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function send(text) {
    const message = (text ?? input).trim();
    if (!message) {
      setError("Please type a question first.");
      return;
    }
    setError("");
    setInput("");
    setMessages((m) => [...m, { role: "user", text: message }]);
    setLoading(true);
    try {
      const res = await api.chat(message);
      setMessages((m) => [
        ...m,
        {
          role: "twin",
          text: res.answer,
          source: res.source,
          factors: res.factors || [],
          missing: res.missing_information || [],
        },
      ]);
    } catch (e) {
      setError(e.message);
      setMessages((m) => [
        ...m,
        {
          role: "twin",
          text: "I couldn't reach my reasoning service just now. Your saved data is safe — nothing was lost. Please try again.",
          source: "error",
          factors: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card
      title="Ask Your Digital Twin"
      subtitle="Answers are grounded in your stored context. Facts, estimates and predictions are labelled."
      className="flex h-[calc(100vh-190px)] min-h-[520px] flex-col"
    >
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"} animate-fade-up`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user" ? "bg-twin-500 text-white" : "border border-white/10 bg-ink-850/80 text-slate-200"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.text}</p>
              {m.role === "twin" && m.factors?.length > 0 && (
                <div className="mt-3 border-t border-white/10 pt-2">
                  <p className="label mb-1.5">Why am I seeing this?</p>
                  <ul className="space-y-1 text-[11px] text-slate-400">
                    {m.factors.map((f, j) => (
                      <li key={j} className="flex gap-2">
                        <span className="text-emerald-400">✓</span>
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {m.role === "twin" && m.missing?.length > 0 && (
                <p className="mt-2 text-[11px] text-amber-300/80">Missing information: {m.missing.join(", ")}</p>
              )}
              {m.role === "twin" && m.source && (
                <div className="mt-2 flex items-center gap-2">
                  <SourceBadge source={m.source === "ai" ? "predicted" : "inferred"} />
                  <span className="text-[10px] text-slate-500">
                    {m.source === "ai" ? "AI-generated reasoning" : "Rule-based TwinEngine"}
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-white/10 bg-ink-850/80 px-4 py-3">
              <Spinner label="Reading your context…" />
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="mt-4 space-y-3">
        <ErrorBanner message={error} />
        <div className="flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              className="chip border-white/10 bg-white/5 text-slate-400 hover:text-slate-200"
              onClick={() => send(s)}
              disabled={loading}
            >
              {s}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Ask your Digital Twin…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !loading && send()}
          />
          <button className="btn-primary" onClick={() => send()} disabled={loading}>
            Send
          </button>
        </div>
      </div>
    </Card>
  );
}