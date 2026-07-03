"use client";

import { FormEvent, useState } from "react";
import { api, QueryResponse } from "@/lib/api";

type Turn = { question: string; response: QueryResponse | null; error?: string };

const SUGGESTIONS = [
  "Which fund had the best January return?",
  "Rank all funds by YTD return.",
  "Which funds are pursuing a distressed or credit-focused strategy?",
];

const TOOL_LABEL: Record<string, string> = {
  run_sql: "SQL (numeric)",
  semantic_search: "Vector search (qualitative)",
};

export function QueryPanel() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);

  const ask = async (q: string) => {
    if (!q.trim() || loading) return;
    setLoading(true);
    setTurns((t) => [...t, { question: q, response: null }]);
    try {
      const response = await api.query(q);
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, response } : turn)));
    } catch (e) {
      setTurns((t) =>
        t.map((turn, i) => (i === t.length - 1 ? { ...turn, error: e instanceof Error ? e.message : "Query failed." } : turn))
      );
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = question;
    setQuestion("");
    ask(q);
  };

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4 flex flex-col h-full">
      <h2 className="text-sm font-semibold text-neutral-200">Ask a question</h2>
      <p className="mt-1 text-xs text-neutral-500">
        Numeric questions run SQL over extracted performance data; qualitative questions search commentary via
        embeddings. The model picks the right tool(s) per question.
      </p>

      {turns.length === 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => ask(s)} className="text-xs rounded-full border border-neutral-700 px-3 py-1 text-neutral-300 hover:bg-neutral-800">
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="mt-4 flex-1 overflow-y-auto space-y-4 max-h-[420px]">
        {turns.map((turn, i) => (
          <div key={i} className="space-y-1.5">
            <p className="text-sm font-medium text-neutral-100">{turn.question}</p>
            {turn.error && <p className="text-sm text-red-400">{turn.error}</p>}
            {!turn.error && !turn.response && <p className="text-sm text-neutral-500 animate-pulse">Thinking…</p>}
            {turn.response && (
              <div className="rounded-lg bg-neutral-950/60 border border-neutral-800 p-3 space-y-2">
                <p className="text-sm text-neutral-200 whitespace-pre-wrap">{turn.response.answer}</p>
                {turn.response.tool_calls.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {turn.response.tool_calls.map((tc, j) => (
                      <span key={j} title={tc.result_preview} className="text-[10px] rounded-full bg-neutral-800 px-2 py-0.5 text-neutral-400">
                        {TOOL_LABEL[tc.tool] ?? tc.tool}
                      </span>
                    ))}
                  </div>
                )}
                {turn.response.source_documents.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {turn.response.source_documents.map((doc) => (
                      <span key={doc} className="text-[10px] rounded-full border border-neutral-700 px-2 py-0.5 text-neutral-500">
                        {doc}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={onSubmit} className="mt-3 flex gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="e.g. Which fund had the best January return?"
          className="flex-1 rounded-lg border border-neutral-700 bg-neutral-900 px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-600"
        />
        <button type="submit" disabled={loading} className="btn-primary">
          Ask
        </button>
      </form>
    </div>
  );
}
