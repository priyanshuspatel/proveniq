"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, fieldMessage, projectsApi } from "@/lib/api";
import { readStore } from "@/lib/storage";
import { INTENDED_USES, IntendedUse, Project, intendedUseLabel } from "@/lib/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [storageWarning, setStorageWarning] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [clientLabel, setClientLabel] = useState("");
  const [intendedUse, setIntendedUse] = useState<IntendedUse>("commercial");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<ApiError | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function load() {
    setLoadError(null);
    try {
      setProjects(await projectsApi.list());
    } catch (error) {
      setProjects([]);
      setLoadError(error instanceof Error ? error.message : "Projects could not be loaded.");
    }
  }

  useEffect(() => {
    setStorageWarning(readStore().warning);
    void load();
  }, []);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    setSuccess(null);
    try {
      const created = await projectsApi.create({
        name,
        client_label: clientLabel.trim() ? clientLabel : null,
        declared_intended_use: intendedUse,
      });
      setName("");
      setClientLabel("");
      setSuccess(`Saved “${created.name}”.`);
      await load();
    } catch (error) {
      setFormError(error instanceof ApiError ? error : new ApiError("The project could not be saved.", 0));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">Projects</h1>
        <p className="mt-3 max-w-prose text-muted">
          Open a job, add the asset you are handing off, then analyze the notice you pasted.
        </p>
        {storageWarning ? <div className="mt-4"><ErrorNote message={storageWarning} /></div> : null}
        <div className="mt-6">
          {projects === null ? <LoadingNote label="Loading projects…" /> : null}
          {loadError ? <ErrorNote message={loadError} /> : null}
          {projects && projects.length === 0 && !loadError ? (
            <EmptyNote title="No projects yet" body="Create a project with the form. The list stays empty until you do." />
          ) : null}
          {projects && projects.length > 0 ? (
            <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-card">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link href={`/projects/${project.id}`} className="block px-5 py-4 no-underline hover:bg-indigo-soft">
                    <span className="text-lg font-medium">{project.name}</span>
                    <span className="mt-1 block text-sm text-muted">
                      {project.client_label || "No client label"} · {intendedUseLabel(project.declared_intended_use)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </section>
      <section className="h-fit rounded-lg border border-line bg-card p-6">
        <h2 className="text-xl font-semibold">New project</h2>
        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium">
            Project name
            <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={name} onChange={(event) => setName(event.target.value)} required maxLength={200} />
            <FieldErrorText message={fieldMessage(formError, "name")} />
          </label>
          <label className="block text-sm font-medium">
            Client label <span className="font-normal text-muted">(optional)</span>
            <input className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={clientLabel} onChange={(event) => setClientLabel(event.target.value)} maxLength={200} />
          </label>
          <label className="block text-sm font-medium">
            Declared intended use
            <select className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2" value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as IntendedUse)}>
              {INTENDED_USES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          {formError ? <ErrorNote message={formError.message} /> : null}
          {success ? <SuccessNote message={success} /> : null}
          <button type="submit" disabled={submitting} className="rounded-md bg-indigo px-4 py-2 text-white disabled:opacity-60">
            {submitting ? "Saving…" : "Create project"}
          </button>
        </form>
      </section>
    </div>
  );
}
