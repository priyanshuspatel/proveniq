"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote, LoadingNote, SuccessNote } from "@/components/Feedback";
import { Button, Card, SectionHeading } from "@/components/ui";
import { reportsApi, type HandoffReport } from "@/lib/api";
import { reportFilename, writeMarkdownInBrowser } from "@/lib/download";

export default function ReportPage({ params }: { params: Promise<{ reportId: string }> }) {
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<HandoffReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState<string | null>(null);

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
  const currentReport = report;

  async function downloadMarkdown() {
    setDownloading(true);
    setError(null);
    setDownloadMessage(null);
    try {
      const version = currentReport.report_version;
      const saved = await writeMarkdownInBrowser(reportFilename(currentReport.project_id, version), currentReport.markdown);
      if (!saved) setError("The Markdown file could not be downloaded.");
      else setDownloadMessage("Markdown download started.");
    } catch (downloadError) {
      setError(downloadError instanceof Error ? downloadError.message : "The Markdown file could not be downloaded.");
    } finally {
      setDownloading(false);
    }
  }

  const includedCount = currentReport.included_asset_count ?? currentReport.included_asset_ids?.length ?? 0;

  return (
    <div className="min-w-0">
      <div className="no-print mb-6 flex flex-wrap items-center justify-between gap-3">
        <Link href={`/projects/${currentReport.project_id}`} className="text-sm font-semibold text-muted hover:text-indigo">← Back to project</Link>
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="secondary" disabled={downloading} busy={downloading} onClick={() => void downloadMarkdown()}>Download Markdown</Button>
          <Button type="button" onClick={() => window.print()}>Print or save as PDF</Button>
        </div>
      </div>
      {error ? <div className="no-print mb-4"><ErrorNote message={error} /></div> : null}
      {downloadMessage ? <div className="no-print mb-4"><SuccessNote message={downloadMessage} /></div> : null}
      <Card className="report-page p-5 sm:p-8">
        <div className="report-header">
          <SectionHeading eyebrow="Handoff record" title={`Report v${currentReport.report_version}`} description="A generated snapshot of the project checks and declarations." />
          <div className="report-meta mt-6" aria-label="Report metadata">
            <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Generated</p><p className="mt-1 font-medium">{currentReport.generated_at ? new Date(currentReport.generated_at).toLocaleString() : "Date unavailable"}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Assets included</p><p className="mt-1 font-medium">{includedCount}</p></div>
            <div><p className="text-xs font-semibold uppercase tracking-wide text-muted">Project</p><p className="mt-1 break-all font-medium">{currentReport.project_id}</p></div>
          </div>
        </div>
        <pre className="report-sheet mt-8 whitespace-pre-wrap break-words text-sm leading-6">{currentReport.markdown}</pre>
        <p className="report-disclaimer mt-8 border-t border-line pt-4 text-sm text-muted">{currentReport.disclaimer}</p>
      </Card>
    </div>
  );
}
