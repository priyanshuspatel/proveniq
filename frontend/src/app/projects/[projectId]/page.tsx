"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, assetsApi, fieldMessage, projectsApi, type AssetInput } from "@/lib/api";
import { DEMO_EXAMPLES, type DemoExample } from "@/lib/examples";
import { writeAssetMeta } from "@/lib/storage";
import { Asset, INTENDED_USES, IntendedUse, Project, intendedUseLabel, reviewStatusLabel } from "@/lib/types";

const inputClass = "mt-1 w-full rounded-md border border-line bg-white px-3 py-2";

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

  if (!projectId || (project === null && !loadError)) return <LoadingNote label="Loading project…" />;

  return (
    <div>
      <Link href="/" className="text-sm text-muted">All projects</Link>
      {loadError ? <div className="mt-4"><ErrorNote message={loadError} /></div> : null}
      {project ? (
        <>
          <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">{project.name}</h1>
              <p className="mt-2 text-muted">
                {project.client_label || "No client label"} · Declared use {intendedUseLabel(project.declared_intended_use)}
              </p>
            </div>
            <button
              type="button"
              className="rounded-md border border-red-300 px-4 py-2 text-sm text-red-900"
              onClick={() => {
                if (!window.confirm(`Delete “${project.name}” and its assets?`)) return;
                void projectsApi.remove(project.id).then(() => router.push("/")).catch((deleteError: unknown) => {
                  setLoadError(deleteError instanceof Error ? deleteError.message : "The project could not be deleted.");
                });
              }}
            >
              Delete project
            </button>
          </div>
          <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_24rem]">
            <section>
              <h2 className="text-xl font-semibold">Asset inventory</h2>
              <div className="mt-4">
                {assets === null ? <LoadingNote label="Loading assets…" /> : null}
                {assets && assets.length === 0 ? (
                  <EmptyNote title="No assets yet" body="Add a file with the form. Nothing is saved until you do." />
                ) : null}
                {assets && assets.length > 0 ? (
                  <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-card">
                    {assets.map((asset) => (
                      <li key={asset.id}>
                        <Link href={`/projects/${project.id}/assets/${asset.id}`} className="block px-5 py-4 no-underline hover:bg-indigo-soft">
                          <span className="text-lg font-medium">{asset.title}</span>
                          <span className="mt-1 block text-sm text-muted">
                            {asset.declared_license} · {reviewStatusLabel(asset.review_status)}
                          </span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </section>
            <section className="h-fit rounded-lg border border-line bg-card p-6">
              <h2 className="text-xl font-semibold">Add asset</h2>
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium">Examples</p>
                <div className="flex flex-wrap gap-2">
                  {DEMO_EXAMPLES.map((example) => (
                    <button key={example.id} type="button" className="rounded-full border border-indigo/30 bg-indigo-soft px-3 py-1 text-sm text-indigo" onClick={() => applyExample(example)}>
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
                <button type="submit" disabled={submitting} className="rounded-md bg-indigo px-4 py-2 text-white disabled:opacity-60">{submitting ? "Saving…" : "Add asset"}</button>
              </form>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
