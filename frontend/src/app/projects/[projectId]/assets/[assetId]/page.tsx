"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, assetsApi, fieldMessage, projectsApi, type ExtractionResult, type ScreeningResult } from "@/lib/api";
import { quotationsFromEvidence, type RestoredQuotation } from "@/lib/restore";
import { readAssetMeta, readStore, writeAssetMeta } from "@/lib/storage";
import { Asset, INTENDED_USES, IntendedUse, Project, intendedUseLabel, reviewStatusLabel } from "@/lib/types";

const inputClass = "mt-1 w-full rounded-md border border-line bg-white px-3 py-2";

export default function AssetPage({ params }: { params: Promise<{ projectId: string; assetId: string }> }) {
  const router = useRouter();
  const [ids, setIds] = useState<{ projectId: string; assetId: string } | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const [assetType, setAssetType] = useState("");
  const [title, setTitle] = useState("");
  const [creator, setCreator] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [declaredLicense, setDeclaredLicense] = useState("");
  const [licenseText, setLicenseText] = useState("");
  const [intendedUse, setIntendedUse] = useState<"" | IntendedUse>("");
  const [attribution, setAttribution] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [saving, setSaving] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [screening, setScreening] = useState(false);
  const [formError, setFormError] = useState<ApiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [extraction, setExtraction] = useState<ExtractionResult | null>(null);
  const [restoredQuotes, setRestoredQuotes] = useState<RestoredQuotation[] | null>(null);
  const [evidenceState, setEvidenceState] = useState<"loading" | "ready" | "error">("loading");
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [assessment, setAssessment] = useState<ScreeningResult | null>(null);

  useEffect(() => {
    void params.then(setIds);
  }, [params]);

  useEffect(() => {
    if (!ids) return;
    const stored = readStore();
    setStorageWarning(stored.warning);
    const meta = readAssetMeta(ids.assetId);
    setAssetType(meta.assetType);
    setConfirmed(meta.confirmed);
    let cancelled = false;
    async function load() {
      try {
        const [nextProject, nextAsset] = await Promise.all([
          projectsApi.get(ids!.projectId),
          assetsApi.get(ids!.assetId),
        ]);
        if (!cancelled) {
          setProject(nextProject);
          setAsset(nextAsset);
          setTitle(nextAsset.title);
          setCreator(nextAsset.creator ?? "");
          setSourceUrl(nextAsset.source_url ?? "");
          setDeclaredLicense(nextAsset.declared_license);
          setLicenseText(nextAsset.supplied_license_text ?? "");
          setIntendedUse(nextAsset.intended_use ?? "");
          setAttribution(nextAsset.attribution_text ?? "");
        }
        try {
          const [evidenceRows, savedScreening] = await Promise.all([
            assetsApi.evidence(ids!.assetId),
            assetsApi.savedScreening(ids!.assetId),
          ]);
          if (!cancelled) {
            setRestoredQuotes(quotationsFromEvidence(evidenceRows));
            setEvidenceState("ready");
            setAssessment(savedScreening.saved ? savedScreening : null);
          }
        } catch (restoreError) {
          if (!cancelled) {
            setEvidenceState("error");
            setEvidenceError(restoreError instanceof Error ? restoreError.message : "Saved evidence could not be loaded.");
          }
        }
      } catch (loadError) {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "This asset could not be loaded.");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [ids]);

  function markOutdated() {
    if (!asset) return;
    setConfirmed(false);
    setAssessment((current) => (current?.saved ? { ...current, outdated: true } : current));
    writeAssetMeta(asset.id, { assetType, confirmed: false });
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!asset) return;
    setSaving(true);
    setFormError(null);
    setSuccess(null);
    try {
      const updated = await assetsApi.update(asset.id, {
        title,
        creator: creator.trim() ? creator : null,
        source_url: sourceUrl.trim() ? sourceUrl : null,
        declared_license: declaredLicense,
        supplied_license_text: licenseText.trim() ? licenseText : null,
        intended_use: intendedUse || null,
        attribution_text: attribution.trim() ? attribution : null,
      });
      setAsset(updated);
      writeAssetMeta(updated.id, { assetType, confirmed: false });
      setConfirmed(false);
      setAssessment((current) => (current?.saved ? { ...current, outdated: true } : null));
      setSuccess("Saved your edits. Confirm the fields again before running the assessment.");
    } catch (saveError) {
      setFormError(saveError instanceof ApiError ? saveError : new ApiError("The asset could not be saved.", 0));
    } finally {
      setSaving(false);
    }
  }

  async function onAnalyze() {
    if (!asset) return;
    setAnalyzing(true);
    setError(null);
    setAssessment(null);
    setConfirmed(false);
    writeAssetMeta(asset.id, { assetType, confirmed: false });
    try {
      const result = await assetsApi.extract(asset.id, assetType || undefined);
      setExtraction(result);
      setRestoredQuotes(
        result.evidence.map((item) => ({
          field: item.field,
          quotation: item.quotation,
          verification_result: item.verification_result,
          verified: item.verification_result === "verified",
        })),
      );
      if (result.recognized_license && result.recognized_license !== "UNKNOWN") {
        setDeclaredLicense(result.recognized_license);
      }
      if (result.creator) setCreator(result.creator);
      if (result.attribution_instructions) setAttribution(result.attribution_instructions);
      setSuccess("Gemma returned candidates. Review the quotations before confirming.");
    } catch (analyzeError) {
      setError(analyzeError instanceof Error ? analyzeError.message : "Analysis failed.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function onConfirm() {
    if (!asset) return;
    setSaving(true);
    setFormError(null);
    try {
      const updated = await assetsApi.update(asset.id, {
        title,
        creator: creator.trim() ? creator : null,
        source_url: sourceUrl.trim() ? sourceUrl : null,
        declared_license: declaredLicense,
        supplied_license_text: licenseText.trim() ? licenseText : null,
        intended_use: intendedUse || null,
        attribution_text: attribution.trim() ? attribution : null,
      });
      setAsset(updated);
      setConfirmed(true);
      writeAssetMeta(updated.id, { assetType, confirmed: true });
      setSuccess("Confirmed. You can run the assessment.");
    } catch (confirmError) {
      setFormError(confirmError instanceof ApiError ? confirmError : new ApiError("Confirmation could not be saved.", 0));
    } finally {
      setSaving(false);
    }
  }

  async function onScreen() {
    if (!asset || !confirmed) return;
    setScreening(true);
    setError(null);
    try {
      const result = await assetsApi.screen(asset.id);
      setAssessment({ ...result, saved: true, outdated: false });
      if (result.review_status) setAsset({ ...asset, review_status: result.review_status });
    } catch (screenError) {
      setError(screenError instanceof Error ? screenError.message : "The assessment could not be run.");
    } finally {
      setScreening(false);
    }
  }

  if (error && !asset) {
    return (
      <div>
        <Link href={ids ? `/projects/${ids.projectId}` : "/"} className="text-sm text-muted">Back to project</Link>
        <div className="mt-4"><ErrorNote message={error} /></div>
      </div>
    );
  }
  if (!asset || !project) return <LoadingNote label="Loading asset…" />;

  return (
    <div className="space-y-8">
      <div>
        <Link href={`/projects/${project.id}`} className="text-sm text-muted">{project.name}</Link>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">{asset.title}</h1>
        <p className="mt-3 max-w-3xl rounded-lg bg-indigo-soft px-4 py-3 text-sm text-indigo">
          {assessment?.saved && assessment.review_status
            ? `Saved assessment: ${reviewStatusLabel(assessment.review_status)}. A pass means the recorded checks succeeded. It is not a legal clearance.`
            : "No assessment has been saved for this asset yet."}
        </p>
        {storageWarning ? <div className="mt-3"><ErrorNote message={storageWarning} /></div> : null}
        {error ? <div className="mt-3"><ErrorNote message={error} /></div> : null}
      </div>

      <section className="rounded-lg border border-line bg-card p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">User-confirmed fields</h2>
          <span className="rounded-full bg-stone-100 px-3 py-1 text-sm">{confirmed ? "Confirmed for assessment" : "Not confirmed"}</span>
        </div>
        <form className="mt-5 grid gap-4 md:grid-cols-2" onSubmit={onSave} onChange={markOutdated}>
          <label className="block text-sm font-medium">Title<input className={inputClass} value={title} onChange={(event) => setTitle(event.target.value)} required /><FieldErrorText message={fieldMessage(formError, "title")} /></label>
          <label className="block text-sm font-medium">Type<input className={inputClass} value={assetType} onChange={(event) => setAssetType(event.target.value)} /></label>
          <label className="block text-sm font-medium">Creator<input className={inputClass} value={creator} onChange={(event) => setCreator(event.target.value)} /></label>
          <label className="block text-sm font-medium">Source URL<input className={inputClass} value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} /><FieldErrorText message={fieldMessage(formError, "source_url")} /></label>
          <label className="block text-sm font-medium">Declared license<input className={inputClass} value={declaredLicense} onChange={(event) => setDeclaredLicense(event.target.value)} required /><FieldErrorText message={fieldMessage(formError, "declared_license")} /></label>
          <label className="block text-sm font-medium">Intended use
            <select className={inputClass} value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as "" | IntendedUse)}>
              <option value="">Not declared</option>
              {INTENDED_USES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
          </label>
          <label className="block text-sm font-medium md:col-span-2">License notice<textarea className={`${inputClass} min-h-28`} value={licenseText} onChange={(event) => setLicenseText(event.target.value)} /></label>
          <label className="block text-sm font-medium md:col-span-2">Attribution text<textarea className={`${inputClass} min-h-20`} value={attribution} onChange={(event) => setAttribution(event.target.value)} /></label>
          {formError ? <div className="md:col-span-2"><ErrorNote message={formError.message} /></div> : null}
          {success ? <div className="md:col-span-2"><SuccessNote message={success} /></div> : null}
          <div className="flex flex-wrap gap-3 md:col-span-2">
            <button type="button" disabled={analyzing} onClick={() => void onAnalyze()} className="rounded-md bg-indigo px-4 py-2 text-white disabled:opacity-60">{analyzing ? "Analyzing…" : "Analyze"}</button>
            <button type="submit" disabled={saving} className="rounded-md border border-line px-4 py-2 disabled:opacity-60">{saving ? "Saving…" : "Save edits"}</button>
            <button type="button" disabled={saving} onClick={() => void onConfirm()} className="rounded-md border border-indigo px-4 py-2 text-indigo disabled:opacity-60">Confirm fields</button>
            <button type="button" disabled={!confirmed || screening} onClick={() => void onScreen()} className="rounded-md bg-stone-900 px-4 py-2 text-white disabled:opacity-40">{screening ? "Checking…" : "Run assessment"}</button>
            <button type="button" className="rounded-md border border-red-300 px-4 py-2 text-red-900" onClick={() => {
              if (!window.confirm(`Delete “${asset.title}”?`)) return;
              void assetsApi.remove(asset.id).then(() => router.push(`/projects/${project.id}`));
            }}>Delete asset</button>
          </div>
        </form>
      </section>

      <section className="rounded-lg border border-indigo/20 bg-card p-6">
        <h2 className="text-xl font-semibold">AI-extracted fields</h2>
        <p className="mt-2 text-sm text-muted">These values come from Gemma and are kept only with a quotation found in the notice. They are not confirmed until you save them above.</p>
        {evidenceState === "loading" ? <div className="mt-4"><LoadingNote label="Loading saved evidence…" /></div> : null}
        {evidenceState === "error" ? <div className="mt-4"><ErrorNote message={evidenceError || "Saved evidence could not be loaded."} /></div> : null}
        {evidenceState === "ready" && !extraction && (restoredQuotes === null || restoredQuotes.length === 0) ? <p className="mt-4 text-muted">No saved quotations.</p> : null}
        {(extraction || (restoredQuotes && restoredQuotes.length > 0)) ? (
          <div className="mt-4 space-y-4">
            {extraction ? <p className="text-sm">{extraction.extraction_note}</p> : <p className="text-sm text-muted">Saved quotations from the last analysis. Missing rows were not treated as verified.</p>}
            {extraction ? (
            <dl className="grid gap-3 md:grid-cols-2">
              <div><dt className="text-sm text-muted">Candidate license</dt><dd className="font-medium">{extraction.recognized_license}</dd></div>
              <div><dt className="text-sm text-muted">Extracted creator</dt><dd className="font-medium">{extraction.creator || "Not extracted"}</dd></div>
              <div><dt className="text-sm text-muted">User-supplied creator</dt><dd className="font-medium">{extraction.user_supplied_creator || "None"}</dd></div>
              <div><dt className="text-sm text-muted">License URL from text</dt><dd className="font-medium break-all">{extraction.license_url || "Not extracted"}</dd></div>
              <div className="md:col-span-2"><dt className="text-sm text-muted">Attribution from text</dt><dd className="font-medium">{extraction.attribution_instructions || "Not extracted"}</dd></div>
            </dl>
            ) : null}
            {extraction && extraction.uncertain_fields.length > 0 ? <p className="text-sm text-muted">Uncertain: {extraction.uncertain_fields.join(", ")}.</p> : null}
            <ul className="space-y-3">
              {(extraction ? extraction.evidence.map((item) => ({ ...item, verified: item.verification_result === "verified" })) : restoredQuotes || []).map((item) => (
                <li key={`${item.field}-${item.quotation}`} className="rounded-md border border-line px-4 py-3 text-sm">
                  <span className="font-medium">{item.field}</span>
                  <span className={item.verified ? "text-muted" : "text-red-800"}> · {item.verified ? item.verification_result : `${item.verification_result} — not verified`}</span>
                  <p className="mt-1">{item.quotation}</p>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>

      <section className="rounded-lg border border-line bg-card p-6">
        <h2 className="text-xl font-semibold">Rule-engine results</h2>
        {!assessment?.saved ? (
          <p className="mt-3 text-muted">{confirmed ? "Run the assessment when the confirmed fields look right." : "Confirm the fields before the assessment runs. Nothing has been assessed yet."}</p>
        ) : (
          <div className="mt-4 space-y-4">
            {assessment.outdated ? <ErrorNote message="These explanations were saved before the fields or evidence changed. Run the assessment again. They are not a new result." /> : null}
            <p className="text-lg font-medium">{assessment.review_status ? reviewStatusLabel(assessment.review_status) : "No status"}</p>
            <p>{assessment.summary}</p>
            <ul className="space-y-3">
              {assessment.rule_results.filter((rule) => rule.outcome !== "pass").map((rule) => (
                <li key={rule.rule_id} className="rounded-md border border-line px-4 py-3 text-sm">
                  <span className="font-medium">{rule.outcome.replaceAll("-", " ")}</span>
                  <p className="mt-1">{rule.explanation}</p>
                </li>
              ))}
            </ul>
            {assessment.rule_results.every((rule) => rule.outcome === "pass") ? <p className="text-sm text-muted">Every recorded check passed. Unscreened rights can still remain.</p> : null}
          </div>
        )}
      </section>
      <p className="text-sm text-muted">Intended use on this asset: {intendedUseLabel(asset.intended_use)}. Project use: {intendedUseLabel(project.declared_intended_use)}.</p>
    </div>
  );
}
