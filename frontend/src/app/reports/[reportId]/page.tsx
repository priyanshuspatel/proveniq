"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote, LoadingNote } from "@/components/Feedback";
import { reportsApi, type HandoffReport } from "@/lib/api";

export default function ReportPage({ params }: { params: Promise<{ reportId: string }> }) {
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<HandoffReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void params.then((value) => setReportId(value.reportId));
  }, [params]);

  useEffect(() => {
    if (!reportId) return;
    let cancelled = false;
    async function load() {
      try {
        const next = await reportsApi.get(reportId as string);
        if (!cancelled) setReport(next);
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "This report could not be loaded.");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  if (!report && !error) return <LoadingNote label="Loading report…" />;
  if (error || !report) return <ErrorNote message={error || "This report could not be loaded."} />;

  return (
    <div>
      <div className="no-print mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link href={`/projects/${report.project_id}`} className="text-sm text-muted">Back to project</Link>
        <button type="button" className="rounded-md bg-indigo px-4 py-2 text-sm text-white" onClick={() => window.print()}>
          Print or save as PDF
        </button>
      </div>
      <pre className="report-sheet whitespace-pre-wrap rounded-lg border border-line bg-card p-6 text-sm leading-6">{report.markdown}</pre>
    </div>
  );
}
