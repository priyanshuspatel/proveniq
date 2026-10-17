"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, assetsApi, fieldMessage, projectsApi } from "@/lib/api";
import { Asset, INTENDED_USES, IntendedUse, Project, intendedUseLabel, reviewStatusLabel } from "@/lib/types";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="border-t border-line py-3">
      <dt className="text-sm text-muted">{label}</dt>
      <dd className="mt-1 whitespace-pre-wrap">{value}</dd>
    </div>
  );
}

export default function AssetPage({
  params,
}: {
  params: Promise<{ projectId: string; assetId: string }>;
}) {
  const [ids, setIds] = useState<{ projectId: string; assetId: string } | null>(null);
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [creator, setCreator] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [declaredLicense, setDeclaredLicense] = useState("");
  const [licenseText, setLicenseText] = useState("");
  const [intendedUse, setIntendedUse] = useState<"" | IntendedUse>("");
  const [attribution, setAttribution] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<ApiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    void params.then(setIds);
  }, [params]);

  useEffect(() => {
    if (!ids) return;
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
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "This asset could not be loaded.");
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [ids]);

  if (error) {
    return (
      <div>
        <Link href={ids ? `/projects/${ids.projectId}` : "/"} className="text-sm text-muted">
          Back to project
        </Link>
        <div className="mt-4">
          <ErrorNote message={error} />
        </div>
      </div>
    );
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
      setSuccess("Saved the asset. Screening has not run.");
    } catch (saveError) {
      setFormError(saveError instanceof ApiError ? saveError : new ApiError("The asset could not be saved.", 0));
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    if (!asset || !project) return;
    if (!window.confirm(`Delete “${asset.title}”? This removes the stored declaration.`)) return;
    try {
      await assetsApi.remove(asset.id);
      router.push(`/projects/${project.id}`);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "The asset could not be deleted.");
    }
  }

  if (!asset || !project) {
    return <LoadingNote label="Loading asset…" />;
  }

  return (
    <div>
      <Link href={`/projects/${project.id}`} className="text-sm text-muted">
        {project.name}
      </Link>
      <h1 className="mt-3 font-serif text-4xl tracking-tight">{asset.title}</h1>
      <p className="mt-3 inline-block rounded-full border border-warn/40 bg-white px-3 py-1 text-sm text-warn">
        {reviewStatusLabel(asset.review_status)}
      </p>
      <p className="mt-3 max-w-prose text-sm text-muted">
        This phase stores the declaration only. Extraction and the rule engine have not run, so this status is not a
        compliance result.
      </p>
      <form className="mt-6 max-w-xl space-y-4 rounded-md border border-line bg-card p-5" onSubmit={onSave}>
        <h2 className="font-serif text-2xl">Edit declaration</h2>
        <label className="block text-sm">
          Title
          <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={300} />
          <FieldErrorText message={fieldMessage(formError, "title")} />
        </label>
        <label className="block text-sm">
          Creator
          <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={creator} onChange={(event) => setCreator(event.target.value)} maxLength={200} />
        </label>
        <label className="block text-sm">
          Source URL
          <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} maxLength={2048} />
          <FieldErrorText message={fieldMessage(formError, "source_url")} />
        </label>
        <label className="block text-sm">
          Declared license
          <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={declaredLicense} onChange={(event) => setDeclaredLicense(event.target.value)} required maxLength={120} />
          <FieldErrorText message={fieldMessage(formError, "declared_license")} />
        </label>
        <label className="block text-sm">
          Supplied license text
          <textarea className="mt-1 min-h-24 w-full rounded-md border border-line bg-white px-3 py-2" value={licenseText} onChange={(event) => setLicenseText(event.target.value)} />
        </label>
        <label className="block text-sm">
          Intended use
          <select className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as "" | IntendedUse)}>
            <option value="">Not declared</option>
            {INTENDED_USES.map((item) => (
              <option key={item.value} value={item.value}>{item.label}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Attribution text
          <textarea className="mt-1 min-h-20 w-full rounded-md border border-line bg-white px-3 py-2" value={attribution} onChange={(event) => setAttribution(event.target.value)} maxLength={2000} />
        </label>
        {formError ? <ErrorNote message={formError.message} /> : null}
        {success ? <SuccessNote message={success} /> : null}
        <div className="flex gap-3">
          <button type="submit" disabled={saving} className="rounded-md bg-clay px-4 py-2 text-white disabled:opacity-60">
            {saving ? "Saving…" : "Save changes"}
          </button>
          <button type="button" onClick={() => void onDelete()} className="rounded-md border border-clay px-4 py-2 text-clay">
            Delete asset
          </button>
        </div>
      </form>
      <dl className="mt-6 max-w-3xl">
        <Fact label="Creator" value={asset.creator ?? "Not supplied"} />
        <Fact label="Source URL" value={asset.source_url ?? "Not supplied"} />
        <Fact label="Declared license" value={asset.declared_license} />
        <Fact label="Supplied license text" value={asset.supplied_license_text ?? "Not supplied"} />
        <Fact label="Intended use" value={intendedUseLabel(asset.intended_use)} />
        <Fact label="Attribution text" value={asset.attribution_text ?? "Not supplied"} />
      </dl>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <section className="rounded-md border border-dashed border-line bg-card p-5">
          <h2 className="font-serif text-2xl">Evidence</h2>
          <p className="mt-2 text-muted">No evidence records yet. Quotations will appear here after extraction.</p>
        </section>
        <section className="rounded-md border border-dashed border-line bg-card p-5">
          <h2 className="font-serif text-2xl">Review results</h2>
          <p className="mt-2 text-muted">No rule results yet. Screening will list them here in a later phase.</p>
        </section>
      </div>
    </div>
  );
}
