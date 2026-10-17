import type { Asset, FieldError, IntendedUse, Project } from "./types";

export class ApiError extends Error {
  status: number;
  details: FieldError[];

  constructor(message: string, status: number, details: FieldError[] = []) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function apiBase(): string {
  const value = process.env.NEXT_PUBLIC_API_URL;
  if (!value) {
    throw new ApiError(
      "NEXT_PUBLIC_API_URL is not set. Copy frontend/.env.example to frontend/.env.local.",
      0,
    );
  }
  return value.replace(/\/$/, "");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError("The API could not be reached. Start the backend, then try again.", 0);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { message?: string; details?: FieldError[] }
      | null;
    throw new ApiError(
      body?.message || "The request failed.",
      response.status,
      body?.details ?? [],
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function fieldMessage(error: unknown, loc: string): string | undefined {
  if (!(error instanceof ApiError)) return undefined;
  return error.details.find((detail) => detail.loc === loc || detail.loc.endsWith(`.${loc}`))?.message;
}

export type ProjectInput = {
  name: string;
  client_label?: string | null;
  declared_intended_use: IntendedUse;
};

export const projectsApi = {
  list: () => request<Project[]>("/api/projects"),
  get: (projectId: string) => request<Project>(`/api/projects/${projectId}`),
  create: (body: ProjectInput) => request<Project>("/api/projects", { method: "POST", body: JSON.stringify(body) }),
  update: (projectId: string, body: Partial<ProjectInput>) =>
    request<Project>(`/api/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (projectId: string) => request<void>(`/api/projects/${projectId}`, { method: "DELETE" }),
};

export type AssetInput = {
  title: string;
  creator?: string | null;
  source_url?: string | null;
  declared_license: string;
  supplied_license_text?: string | null;
  intended_use?: IntendedUse | null;
  attribution_text?: string | null;
};

export const assetsApi = {
  list: (projectId: string) => request<Asset[]>(`/api/projects/${projectId}/assets`),
  get: (assetId: string) => request<Asset>(`/api/assets/${assetId}`),
  create: (projectId: string, body: AssetInput) =>
    request<Asset>(`/api/projects/${projectId}/assets`, { method: "POST", body: JSON.stringify(body) }),
  update: (assetId: string, body: Partial<AssetInput>) =>
    request<Asset>(`/api/assets/${assetId}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (assetId: string) => request<void>(`/api/assets/${assetId}`, { method: "DELETE" }),
};
