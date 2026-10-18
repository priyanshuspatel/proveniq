import type { Project } from "./types";

export type ProjectFilter = "all" | "needs-review" | "ready";

export function filterProjects(projects: Project[], query: string, filter: ProjectFilter): Project[] {
  const needle = query.trim().toLocaleLowerCase();
  return projects.filter((project) => {
    const matchesQuery = !needle || [project.name, project.client_label ?? ""].some((value) =>
      value.toLocaleLowerCase().includes(needle),
    );
    const matchesFilter =
      filter === "all" ||
      (filter === "ready" && project.review_status === "supported-checks-passed") ||
      (filter === "needs-review" && project.review_status !== "supported-checks-passed");
    return matchesQuery && matchesFilter;
  });
}
