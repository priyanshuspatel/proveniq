"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { Button, Card, SectionHeading, StatusBadge } from "@/components/ui";
import { ApiError, assetsApi, fieldMessage, projectsApi, reportsApi, type AssetInput } from "@/lib/api";
import { reportFilename, saveGeneratedReport, writeMarkdownInBrowser } from "@/lib/download";
import { DEMO_EXAMPLES, type DemoExample } from "@/lib/examples";
import { readAssetMeta, writeAssetMeta } from "@/lib/storage";
import { Asset, INTENDED_USES, IntendedUse, Project, intendedUseLabel, reviewStatusLabel } from "@/lib/types";

const inputClass = "field-control";

export default function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [assetType, setAssetType] = useState("");
  const [creator, setCreator] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [declaredLicense, setDeclaredLicense] = useState("");
  const [licenseText, setLicenseText] = useState("");
  const [intendedUse, setIntendedUse] = useState<"" | IntendedUse>("");
  const [exampleNote, setExampleNote] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<ApiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [reportError, setReportError] = useState<string | null>(null);
  const [reportMessage, setReportMessage] = useState<string | null>(null);
  const [reportHref, setReportHref] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [reportHistory, setReportHistory] = useState<Awaited<ReturnType<typeof reportsApi.list>> | null>(null);
  const [reportHistoryLoading, setReportHistoryLoading] = useState(true);
  const [reportHistoryError, setReportHistoryError] = useState<string | null>(null);

  useEffect(() => {
    void params.then((value) => setProjectId(value.projectId));
  }, [params]);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    async function load() {
      setLoadError(null);
      try {
        const [nextProject, nextAssets] = await Promise.all([
          projectsApi.get(projectId as string),
          assetsApi.list(projectId as string),
        ]);
        if (!cancelled) {
          setProject(nextProject);
          setAssets(nextAssets);
        }
        setReportHistoryLoading(true);
        setReportHistoryError(null);
        try {
          const reports = await reportsApi.list(projectId as string);
          if (!cancelled) setReportHistory(reports);
        } catch (reportError) {
          if (!cancelled) setReportHistoryError(reportError instanceof Error ? reportError.message : "Report history could not be loaded.");
        } finally {
          if (!cancelled) setReportHistoryLoading(false);
        }
      } catch (error) {
        if (!cancelled) {
          setProject(null);
          setAssets([]);
          setLoadError(error instanceof Error ? error.message : "This project could not be loaded.");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [projectId, success]);

  function applyExample(example: DemoExample) {
    setTitle(example.title);
    setAssetType(example.assetType);
    setCreator(example.creator);
    setSourceUrl(example.sourceUrl);
    setDeclaredLicense(example.declaredLicense);
    setLicenseText(example.licenseText);
    setIntendedUse(example.intendedUse);
    setExampleNote(example.note);
    setSuccess(null);
    setFormError(null);
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!projectId) return;
    setSubmitting(true);
    setFormError(null);
    setSuccess(null);
    const body: AssetInput = {
      title,
      declared_license: declaredLicense,
      creator: creator.trim() ? creator : null,
      source_url: sourceUrl.trim() ? sourceUrl : null,
      supplied_license_text: licenseText.trim() ? licenseText : null,
      intended_use: intendedUse || null,
    };
    try {
      const created = await assetsApi.create(projectId, body);
      writeAssetMeta(created.id, { assetType, confirmed: false });
      setTitle("");
      setAssetType("");
      setCreator("");
      setSourceUrl("");
      setDeclaredLicense("");
      setLicenseText("");
      setIntendedUse("");
      setExampleNote(null);
      setSuccess(`Saved “${created.title}”. Open it to analyze the notice.`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error : new ApiError("The asset could not be saved.", 0));
    } finally {
      setSubmitting(false);
    }
  }

  async function downloadReport() {
    if (!projectId || !assets) return;
    setDownloading(true);
    setReportError(null);
    setReportMessage(null);
    setReportHref(null);
    try {
      const assetTypes: Record<string, string> = {};
      for (const asset of assets) {
        const assetType = readAssetMeta(asset.id).assetType.trim();
        if (assetType) assetTypes[asset.id] = assetType;
      }
      const report = await reportsApi.create(projectId, assetTypes);
      const filename = await saveGeneratedReport(
        report.markdown,
        reportFilename(projectId, report.report_version),
        writeMarkdownInBrowser,
      );
      try {
        setReportHistory(await reportsApi.list(projectId));
        setReportHistoryError(null);
      } catch {
        // The generated report is still usable when the optional history refresh fails.
      }
      setReportHref(`/reports/${report.id}`);
      setReportMessage(`Downloaded ${filename}.`);
    } catch (error) {
      setReportError(error instanceof Error ? error.message : "The report could not be downloaded.");
    } finally {
      setDownloading(false);
    }
  }

  if (!projectId || (project === null && !loadError)) return <LoadingNote label="Loading project…" />;

  return (
    <div>
      <Link href="/" className="text-sm text-muted">All projects</Link>
      {loadError ? <div className="mt-4"><ErrorNote message={loadError} /></div> : null}
      {project ? (
        <>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="eyebrow">Project workspace</p>
                <h1 className="text-3xl font-semibold tracking-tight">{project.name}</h1>
              <p className="mt-2 text-muted">
                {project.client_label || "No client label"} · Declared use {intendedUseLabel(project.declared_intended_use)}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
               <Button
                 type="button"
                 className="w-full sm:w-auto"
                 disabled={downloading || assets === null}
                 busy={downloading}
                 onClick={() => void downloadReport()}
               >
                  {downloading ? "Preparing report…" : "Download Markdown report"}
               </Button>
               <Button
                 type="button"
                 variant="danger"
                  disabled={deleting || downloading}
                  busy={deleting}
                  onClick={() => {
                 if (!window.confirm(`Delete “${project.name}” and its assets?`)) return;
                 setDeleting(true);
                 void projectsApi.remove(project.id).then(() => router.push("/")).catch((deleteError: unknown) => {
                   setLoadError(deleteError instanceof Error ? deleteError.message : "The project could not be deleted.");
                 }).finally(() => setDeleting(false));
               }}
               >
                  {deleting ? "Deleting project…" : "Delete project"}
               </Button>
            </div>
          </div>
          {reportError ? <div className="mt-4"><ErrorNote message={reportError} /></div> : null}
          {reportMessage ? (
            <div className="mt-4">
              <SuccessNote message={reportMessage} />
              {reportHref ? <Link href={reportHref} className="mt-2 inline-block text-sm text-indigo">Open the print view</Link> : null}
            </div>
          ) : null}
          <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_24rem]">
            <section>
              <SectionHeading eyebrow="What you are handing off" title="Asset inventory" description={assets ? `${assets.length} ${assets.length === 1 ? "asset" : "assets"} in this project` : "Loading the project assets"} />
              <div className="mt-4">
                {assets === null ? <LoadingNote label="Loading assets…" /> : null}
                {assets && assets.length === 0 ? (
                  <EmptyNote title="No assets yet" body="Add a file with the form. Nothing is saved until you do." />
                ) : null}
                {assets && assets.length > 0 ? (
                   <ul className="grid gap-3">
                     {assets.map((asset) => (
                       <li key={asset.id}>
                         <Link href={`/projects/${project.id}/assets/${asset.id}`} className="surface-card block p-5 no-underline transition hover:border-indigo hover:shadow-md">
                           <div className="flex flex-wrap items-start justify-between gap-3">
                             <span className="min-w-0 text-lg font-semibold">{asset.title}</span>
                             <StatusBadge status={asset.review_status} />
                           </div>
                           <span className="mt-2 block break-words text-sm text-muted">{asset.declared_license} · {reviewStatusLabel(asset.review_status)}</span>
                         </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </section>
             <Card className="h-fit p-6">
               <SectionHeading eyebrow="Build the record" title="Add asset" description="Paste the license notice you have. Nothing is inferred from the source URL." />
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium">Examples</p>
                <div className="flex flex-wrap gap-2">
                  {DEMO_EXAMPLES.map((example) => (
                     <button key={example.id} type="button" className="rounded-full border border-indigo/30 bg-indigo-soft px-3 py-1 text-sm font-semibold text-indigo hover:border-indigo" onClick={() => applyExample(example)}>
                      {example.label}
                    </button>
                  ))}
                </div>
                {exampleNote ? <p className="text-sm text-muted">{exampleNote}</p> : null}
              </div>
              <form className="mt-5 space-y-4" onSubmit={onSubmit}>
                <label className="block text-sm font-medium">Title<input className={inputClass} value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={300} /><FieldErrorText message={fieldMessage(formError, "title")} /></label>
                <label className="block text-sm font-medium">Type<input className={inputClass} value={assetType} onChange={(event) => setAssetType(event.target.value)} placeholder="image, font, illustration" /></label>
                <label className="block text-sm font-medium">Creator <span className="font-normal text-muted">(if known)</span><input className={inputClass} value={creator} onChange={(event) => setCreator(event.target.value)} maxLength={200} /></label>
                <label className="block text-sm font-medium">Source URL<input className={inputClass} value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} maxLength={2048} placeholder="https://" /><FieldErrorText message={fieldMessage(formError, "source_url")} /></label>
                <label className="block text-sm font-medium">Declared license<input className={inputClass} value={declaredLicense} onChange={(event) => setDeclaredLicense(event.target.value)} required maxLength={120} /><FieldErrorText message={fieldMessage(formError, "declared_license")} /></label>
                <label className="block text-sm font-medium">License notice<textarea className={`${inputClass} min-h-28`} value={licenseText} onChange={(event) => setLicenseText(event.target.value)} /></label>
                <label className="block text-sm font-medium">Intended use
                  <select className={inputClass} value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as "" | IntendedUse)}>
                    <option value="">Not declared</option>
                    {INTENDED_USES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
                  </select>
                </label>
                {formError ? <ErrorNote message={formError.message} /> : null}
                {success ? <SuccessNote message={success} /> : null}
                 <Button type="submit" disabled={submitting} busy={submitting}>{submitting ? "Saving asset…" : "Add asset"}</Button>
               </form>
             </Card>
           </div>
           <section className="mt-8">
             <SectionHeading eyebrow="A durable trail" title="Report history" description="Open a previous handoff report to print or save it again." />
             <div className="mt-4">
               {reportHistoryLoading ? <LoadingNote label="Loading report history…" /> : null}
               {reportHistoryError ? <ErrorNote message={reportHistoryError} /> : null}
               {!reportHistoryLoading && !reportHistoryError && reportHistory?.length === 0 ? <EmptyNote title="No reports yet" body="Generate a Markdown report when the asset records are ready. Previous versions will appear here." /> : null}
               {reportHistory && reportHistory.length > 0 ? (
                 <div className="surface-card overflow-hidden">
                   <ul className="divide-y divide-line">
                     {reportHistory.map((report) => (
                       <li key={report.id} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
                         <div>
                           <p className="font-semibold">Report v{report.report_version}</p>
                           <p className="mt-1 text-sm text-muted">{new Date(report.generated_at).toLocaleString()} · {report.included_asset_count} {report.included_asset_count === 1 ? "asset" : "assets"} included</p>
                         </div>
                         <Link href={`/reports/${report.id}`} className="text-sm font-semibold text-indigo hover:underline">Open report <span aria-hidden="true">→</span></Link>
                       </li>
                     ))}
                   </ul>
                 </div>
               ) : null}
             </div>
           </section>
         </>
      ) : null}
    </div>
  );
}
