"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { EmptyNote, ErrorNote, FieldErrorText, LoadingNote, SuccessNote } from "@/components/Feedback";
import { Button, Card, SectionHeading, StatusBadge } from "@/components/ui";
import { ApiError, fieldMessage, projectsApi } from "@/lib/api";
import { filterProjects, type ProjectFilter } from "@/lib/projectFilters";
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
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<ProjectFilter>("all");

  async function load() {
    setLoadError(null);
    try {
      setProjects(await projectsApi.list());
    } catch (error) {
      setProjects([]);
      setLoadError(error instanceof Error ? error.message : "Projects could not be loaded.");
    }
  }

  const visibleProjects = projects ? filterProjects(projects, query, filter) : [];

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
    <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_23rem] lg:gap-10">
      <section>
        <p className="eyebrow">License desk</p>
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Projects</h1>
        <p className="mt-3 max-w-prose text-muted">Keep each client handoff together. Start with a project, add its assets, then review the source notices before you deliver.</p>
        {storageWarning ? <div className="mt-4"><ErrorNote message={storageWarning} /></div> : null}
        <div className="mt-6">
          {projects === null ? <LoadingNote label="Loading projects…" /> : null}
          {loadError ? <ErrorNote message={loadError} /> : null}
          {projects && projects.length === 0 && !loadError ? (
            <EmptyNote title="Your desk is ready" body="Create your first project to keep asset notices, checks, and handoff reports in one place." />
          ) : null}
          {projects && projects.length > 0 ? (
            <>
              <div className="surface-card mb-4 flex flex-col gap-3 p-4 sm:flex-row">
                <label className="min-w-0 flex-1 text-sm font-semibold">
                  <span className="sr-only">Search projects</span>
                  <input className="mt-0 w-full rounded-lg border border-line bg-white px-3 py-2 font-normal placeholder:text-muted" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search projects or clients" type="search" />
                </label>
                <label className="text-sm font-semibold sm:w-44">
                  <span className="sr-only">Filter projects</span>
                  <select className="mt-0 w-full rounded-lg border border-line bg-white px-3 py-2 font-normal" value={filter} onChange={(event) => setFilter(event.target.value as ProjectFilter)}>
                    <option value="all">All projects</option>
                    <option value="needs-review">Needs review</option>
                    <option value="ready">Checks passed</option>
                  </select>
                </label>
              </div>
              {visibleProjects.length === 0 ? <EmptyNote title="No matching projects" body="Try a different search or clear the filter." /> : null}
              {visibleProjects.length > 0 ? <ul className="grid gap-3 sm:grid-cols-2">
              {visibleProjects.map((project) => (
                <li key={project.id}>
                  <Link href={`/projects/${project.id}`} className="surface-card block h-full p-5 no-underline transition hover:-translate-y-0.5 hover:border-indigo hover:shadow-md">
                    <div className="flex items-start justify-between gap-3">
                      <span className="min-w-0 text-lg font-semibold">{project.name}</span>
                      <StatusBadge status={project.review_status} />
                    </div>
                    <span className="mt-2 block break-words text-sm text-muted">{project.client_label || "No client label"}</span>
                    <span className="mt-3 block text-xs font-medium uppercase tracking-wide text-muted">{project.asset_count === undefined ? "Asset count unavailable" : `${project.asset_count} ${project.asset_count === 1 ? "asset" : "assets"}`} · {intendedUseLabel(project.declared_intended_use)}</span>
                  </Link>
                </li>
              ))}
              </ul> : null}
            </>
          ) : null}
        </div>
      </section>
      <Card className="h-fit p-6">
        <SectionHeading eyebrow="Get started" title="New project" description="Give the workspace a name and intended use. You can add assets next." />
        <form className="mt-5 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium">
            Project name
            <input className="field-control" value={name} onChange={(event) => setName(event.target.value)} required maxLength={200} />
            <FieldErrorText message={fieldMessage(formError, "name")} />
          </label>
          <label className="block text-sm font-medium">
            Client label <span className="font-normal text-muted">(optional)</span>
            <input className="field-control" value={clientLabel} onChange={(event) => setClientLabel(event.target.value)} maxLength={200} />
          </label>
          <label className="block text-sm font-medium">
            Declared intended use
            <select className="field-control" value={intendedUse} onChange={(event) => setIntendedUse(event.target.value as IntendedUse)}>
              {INTENDED_USES.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </select>
          </label>
          {formError ? <ErrorNote message={formError.message} /> : null}
          {success ? <SuccessNote message={success} /> : null}
          <Button type="submit" disabled={submitting} busy={submitting}>{submitting ? "Creating project…" : "Create project"}</Button>
        </form>
      </Card>
    </div>
  );
}
