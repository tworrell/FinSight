"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import { api, Document, Fund } from "@/lib/api";

const STATUS_STYLES: Record<string, string> = {
  done: "bg-emerald-900/40 text-emerald-300",
  processing: "bg-amber-900/40 text-amber-300",
  pending: "bg-neutral-800 text-neutral-400",
  error: "bg-red-900/40 text-red-300",
};

export function DocumentsTable({ refreshKey }: { refreshKey: number }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [funds, setFunds] = useState<Fund[]>([]);
  const [fundFilter, setFundFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.funds().then(setFunds).catch(() => {});
  }, [refreshKey]);

  useEffect(() => {
    setLoading(true);
    api
      .documents({ fund_id: fundFilter || undefined, status: statusFilter || undefined })
      .then(setDocuments)
      .finally(() => setLoading(false));
  }, [fundFilter, statusFilter, refreshKey]);

  const rows = useMemo(
    () =>
      documents.map((d) => ({
        doc: d,
        extraction: d.extractions[0] ?? null,
      })),
    [documents]
  );

  return (
    <div className="rounded-xl border border-neutral-800 bg-neutral-900/60 p-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="text-sm font-semibold text-neutral-200">Ingested documents ({documents.length})</h2>
        <div className="flex gap-2">
          <select
            value={fundFilter}
            onChange={(e) => setFundFilter(e.target.value)}
            className="text-sm rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
          >
            <option value="">All funds</option>
            {funds.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-sm rounded-lg border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-200"
          >
            <option value="">All statuses</option>
            <option value="done">Done</option>
            <option value="processing">Processing</option>
            <option value="pending">Pending</option>
            <option value="error">Error</option>
          </select>
        </div>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-neutral-500 border-b border-neutral-800">
              <th className="py-2 pr-4 font-medium">File</th>
              <th className="py-2 pr-4 font-medium">Fund</th>
              <th className="py-2 pr-4 font-medium">Type</th>
              <th className="py-2 pr-4 font-medium">As of</th>
              <th className="py-2 pr-4 font-medium">YTD</th>
              <th className="py-2 pr-4 font-medium">Source</th>
              <th className="py-2 pr-4 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="py-4 text-center text-neutral-500">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="py-4 text-center text-neutral-500">
                  No documents yet — connect Drive or upload a file to get started.
                </td>
              </tr>
            )}
            {rows.map(({ doc, extraction }) => (
              <Fragment key={doc.id}>
                <tr
                  onClick={() => setExpanded(expanded === doc.id ? null : doc.id)}
                  className="border-b border-neutral-900 hover:bg-neutral-800/40 cursor-pointer transition"
                >
                  <td className="py-2 pr-4 text-neutral-200 max-w-[180px] truncate whitespace-nowrap" title={doc.filename}>
                    {doc.filename}
                  </td>
                  <td className="py-2 pr-4 text-neutral-300 max-w-[160px] truncate whitespace-nowrap" title={extraction?.fund?.name ?? ""}>
                    {extraction?.fund?.name ?? "—"}
                  </td>
                  <td className="py-2 pr-4 text-neutral-400 whitespace-nowrap">{extraction?.document_type ?? "—"}</td>
                  <td className="py-2 pr-4 text-neutral-400 whitespace-nowrap">{extraction?.as_of_date ?? "—"}</td>
                  <td className="py-2 pr-4 text-neutral-400 whitespace-nowrap">
                    {extraction?.performance_records?.[0]?.ytd_return_pct != null
                      ? `${extraction.performance_records[0].ytd_return_pct}%`
                      : "—"}
                  </td>
                  <td className="py-2 pr-4 text-neutral-500 whitespace-nowrap">{doc.source}</td>
                  <td className="py-2 pr-4 whitespace-nowrap">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_STYLES[doc.status]}`}>{doc.status}</span>
                  </td>
                </tr>
                {expanded === doc.id && (
                  <tr className="bg-neutral-950/60">
                    <td colSpan={7} className="p-4">
                      {doc.status === "error" ? (
                        <p className="text-sm text-red-400">{doc.error_message}</p>
                      ) : extraction ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <h3 className="text-xs font-semibold uppercase text-neutral-500 mb-1">Commentary</h3>
                            <p className="text-sm text-neutral-300">{extraction.commentary_text ?? "—"}</p>
                            {extraction.low_confidence_fields.length > 0 && (
                              <p className="mt-2 text-xs text-amber-400">
                                Low-confidence fields: {extraction.low_confidence_fields.join(", ")}
                              </p>
                            )}
                          </div>
                          <div>
                            <h3 className="text-xs font-semibold uppercase text-neutral-500 mb-1">Monthly returns</h3>
                            <table className="w-full text-xs">
                              <thead>
                                <tr className="text-neutral-500">
                                  <th className="text-left pr-3 py-1">Month</th>
                                  <th className="text-left pr-3 py-1">Return</th>
                                  <th className="text-left pr-3 py-1">NAV</th>
                                </tr>
                              </thead>
                              <tbody>
                                {extraction.performance_records.map((p, i) => (
                                  <tr key={i} className="text-neutral-300">
                                    <td className="pr-3 py-0.5">{p.period_month}</td>
                                    <td className="pr-3 py-0.5">{p.return_pct != null ? `${p.return_pct}%` : "—"}</td>
                                    <td className="pr-3 py-0.5">{p.nav ?? "—"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ) : (
                        <p className="text-sm text-neutral-500">Still processing…</p>
                      )}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
