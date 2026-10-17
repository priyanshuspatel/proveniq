"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { ApiError, fieldMessage, projectsApi } from "@/lib/api";
import { INTENDED_USES, IntendedUse, Project, intendedUseLabel } from "@/lib/types";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
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
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
      <section>
        <h1 className="font-serif text-4xl tracking-tight">Projects</h1>
        <p className="mt-2 max-w-prose text-muted">
          Start a handoff by naming the job and the use you declared. Assets are added on the project page.
        </p>
        <div className="mt-6">
          {projects === null ? <LoadingNote label="Loading projects…" /> : null}
          {loadError ? <ErrorNote message={loadError} /> : null}
          {projects && projects.length === 0 && !loadError ? (
            <EmptyNote
              title="No projects yet"
              body="Create the first project with the form. Nothing here is sample data."
            />
          ) : null}
          {projects && projects.length > 0 ? (
            <ul className="divide-y divide-line overflow-hidden rounded-md border border-line bg-card">
              {projects.map((project) => (
                <li key={project.id}>
                  <Link href={`/projects/${project.id}`} className="block px-5 py-4 no-underline hover:bg-paper">
                    <span className="font-serif text-xl">{project.name}</span>
                    <span className="mt-1 block text-sm text-muted">
                      {project.client_label ? project.client_label : "No client label"} ·{" "}
                      {intendedUseLabel(project.declared_intended_use)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </section>
      <section className="h-fit rounded-md border border-line bg-card p-5">
        <h2 className="font-serif text-2xl">New project</h2>
        <form className="mt-4 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm">
            Project name
            <input
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2"
              value={name}
              onChange={(event) => setName(event.target.value)}
              required
              maxLength={200}
            />
            <FieldErrorText message={fieldMessage(formError, "name")} />
          </label>
          <label className="block text-sm">
            Client label <span className="text-muted">(optional)</span>
            <input
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2"
              value={clientLabel}
              onChange={(event) => setClientLabel(event.target.value)}
              maxLength={200}
            />
            <FieldErrorText message={fieldMessage(formError, "client_label")} />
          </label>
          <label className="block text-sm">
            Declared intended use
            <select
              className="mt-1 w-full rounded-md border border-line bg-white px-3 py-2"
              value={intendedUse}
              onChange={(event) => setIntendedUse(event.target.value as IntendedUse)}
            >
              {INTENDED_USES.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <FieldErrorText message={fieldMessage(formError, "declared_intended_use")} />
          </label>
          {formError ? <ErrorNote message={formError.message} /> : null}
          {success ? <SuccessNote message={success} /> : null}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-clay px-4 py-2 text-white disabled:opacity-60"
          >
            {submitting ? "Saving…" : "Create project"}
          </button>
        </form>
      </section>
    </div>
  );
}
