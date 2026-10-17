"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, assetsApi, fieldMessage, projectsApi, type AssetInput } from "@/lib/api";
import { Asset, INTENDED_USES, IntendedUse, Project, intendedUseLabel, reviewStatusLabel } from "@/lib/types";

export default function ProjectPage({ params }: { params: Promise<{ projectId: string }> }) {
  const router = useRouter();
  const [projectId, setProjectId] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [creator, setCreator] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [declaredLicense, setDeclaredLicense] = useState("");
  const [licenseText, setLicenseText] = useState("");
  const [intendedUse, setIntendedUse] = useState<"" | IntendedUse>("");
  const [attribution, setAttribution] = useState("");
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
      attribution_text: attribution.trim() ? attribution : null,
    };
    try {
      const created = await assetsApi.create(projectId, body);
      setTitle("");
      setCreator("");
      setSourceUrl("");
      setDeclaredLicense("");
      setLicenseText("");
      setIntendedUse("");
      setAttribution("");
      setSuccess(`Saved “${created.title}”. Screening has not run.`);
    } catch (error) {
      setFormError(error instanceof ApiError ? error : new ApiError("The asset could not be saved.", 0));
    } finally {
      setSubmitting(false);
    }
  }

  if (!projectId || (project === null && !loadError)) {
    return <LoadingNote label="Loading project…" />;
  }

  return (
    <div>
      <Link href="/" className="text-sm text-muted">
        All projects
      </Link>
      {loadError ? (
        <div className="mt-4">
          <ErrorNote message={loadError} />
        </div>
      ) : null}
      {project ? (
        <>
          <h1 className="mt-3 font-serif text-4xl tracking-tight">{project.name}</h1>
          <p className="mt-2 text-muted">
            {project.client_label ? project.client_label : "No client label"} · Declared use{" "}
            {intendedUseLabel(project.declared_intended_use)}
          </p>
          <button
            type="button"
            className="mt-4 rounded-md border border-clay px-4 py-2 text-sm text-clay"
            onClick={() => {
              if (!window.confirm(`Delete “${project.name}” and its assets?`)) return;
              void projectsApi.remove(project.id).then(() => router.push("/")).catch((deleteError: unknown) => {
                setLoadError(deleteError instanceof Error ? deleteError.message : "The project could not be deleted.");
              });
            }}
          >
            Delete project
          </button>
          <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <section>
              <h2 className="font-serif text-2xl">Asset inventory</h2>
              <div className="mt-4">
                {assets === null ? <LoadingNote label="Loading assets…" /> : null}
                {assets && assets.length === 0 ? (
                  <EmptyNote title="No assets yet" body="Add the first file with the form. The list stays empty until you do." />
                ) : null}
                {assets && assets.length > 0 ? (
                  <ul className="divide-y divide-line overflow-hidden rounded-md border border-line bg-card">
                    {assets.map((asset) => (
                      <li key={asset.id}>
                        <Link
                          href={`/projects/${project.id}/assets/${asset.id}`}
                          className="block px-5 py-4 no-underline hover:bg-paper"
                        >
                          <span className="font-serif text-xl">{asset.title}</span>
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
            <section className="h-fit rounded-md border border-line bg-card p-5">
              <h2 className="font-serif text-2xl">Add asset</h2>
              <form className="mt-4 space-y-4" onSubmit={onSubmit}>
                <label className="block text-sm">
                  Title
                  <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={300} />
                  <FieldErrorText message={fieldMessage(formError, "title")} />
                </label>
                <label className="block text-sm">
                  Creator <span className="text-muted">(optional)</span>
                  <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={creator} onChange={(event) => setCreator(event.target.value)} maxLength={200} />
                  <FieldErrorText message={fieldMessage(formError, "creator")} />
                </label>
                <label className="block text-sm">
                  Source URL <span className="text-muted">(optional, http or https)</span>
                  <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={sourceUrl} onChange={(event) => setSourceUrl(event.target.value)} maxLength={2048} placeholder="https://" />
                  <FieldErrorText message={fieldMessage(formError, "source_url")} />
                </label>
                <label className="block text-sm">
                  Declared license
                  <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={declaredLicense} onChange={(event) => setDeclaredLicense(event.target.value)} required maxLength={120} placeholder="CC-BY-4.0" />
                  <FieldErrorText message={fieldMessage(formError, "declared_license")} />
                </label>
                <label className="block text-sm">
                  Supplied license text <span className="text-muted">(optional)</span>
                  <textarea className="mt-1 min-h-28 w-full rounded-md border border-line bg-white px-3 py-2" value={licenseText} onChange={(event) => setLicenseText(event.target.value)} />
                  <FieldErrorText message={fieldMessage(formError, "supplied_license_text")} />
                </label>
                <label className="block text-sm">
                  Intended use <span className="text-muted">(optional)</span>
                  <select className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as "" | IntendedUse)}>
                    <option value="">Not declared</option>
                    {INTENDED_USES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  <FieldErrorText message={fieldMessage(formError, "intended_use")} />
                </label>
                <label className="block text-sm">
                  Attribution text <span className="text-muted">(optional)</span>
                  <textarea className="mt-1 min-h-20 w-full rounded-md border border-line bg-white px-3 py-2" value={attribution} onChange={(event) => setAttribution(event.target.value)} maxLength={2000} />
                  <FieldErrorText message={fieldMessage(formError, "attribution_text")} />
                </label>
                {formError ? <ErrorNote message={formError.message} /> : null}
                {success ? <SuccessNote message={success} /> : null}
                <button type="submit" disabled={submitting} className="rounded-md bg-clay px-4 py-2 text-white disabled:opacity-60">
                  {submitting ? "Saving…" : "Add asset"}
                </button>
              </form>
            </section>
          </div>
        </>
      ) : null}
    </div>
  );
}
