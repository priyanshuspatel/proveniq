import type { Asset, FieldError, IntendedUse, Project, ReviewStatus } from "./types";

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

export type HandoffReport = {
  id: string;
  project_id: string;
  generated_at?: string;
  report_version: number;
  markdown: string;
  disclaimer: string;
  included_asset_ids?: string[];
  included_asset_count?: number;
};

export type ReportSummary = {
  id: string;
  project_id: string;
  generated_at: string;
  report_version: number;
  included_asset_count: number;
};

export const reportsApi = {
  create: (projectId: string, assetTypes: Record<string, string>) =>
    request<HandoffReport>(`/api/projects/${projectId}/reports`, {
      method: "POST",
      body: JSON.stringify({ asset_types: assetTypes }),
    }),
  get: (reportId: string) => request<HandoffReport>(`/api/reports/${reportId}`),
  list: (projectId: string) => request<ReportSummary[]>(`/api/projects/${projectId}/reports`),
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
  evidence: (assetId: string) => request<StoredEvidence[]>(`/api/assets/${assetId}/evidence`),
  savedScreening: (assetId: string) => request<ScreeningResult>(`/api/assets/${assetId}/screening`),
  extract: (assetId: string, assetType?: string) => {
    const query = assetType ? `?asset_type=${encodeURIComponent(assetType)}` : "";
    return request<ExtractionResult>(`/api/assets/${assetId}/extractions${query}`, { method: "POST" });
  },
  screen: (assetId: string) => request<ScreeningResult>(`/api/assets/${assetId}/screening`, { method: "POST" }),
  analyze: (body: AnalyzeRequest) => request<ExtractionResult>("/api/analyze", { method: "POST", body: JSON.stringify(body) }),
};

export type AnalyzeRequest = {
  title: string;
  asset_type?: string | null;
  creator?: string | null;
  source_url?: string | null;
  license_text: string;
};

export type ExtractionEvidence = {
  field: string;
  quotation: string;
  verification_result: string;
};

export type ExtractionResult = {
  recognized_license: string;
  creator: string | null;
  license_url: string | null;
  attribution_instructions: string | null;
  uncertain_fields: string[];
  evidence: ExtractionEvidence[];
  review_status: ReviewStatus;
  extraction_note: string | null;
  user_supplied_creator?: string | null;
};

export type RuleResult = {
  rule_id: string;
  outcome: string;
  explanation: string;
};

export type StoredEvidence = {
  id: string;
  quotation: string | null;
  verification_status: string;
  condition_type: string | null;
  source_reference: string | null;
};

export type ScreeningResult = {
  asset_id: string;
  saved?: boolean;
  outdated?: boolean;
  review_status?: ReviewStatus;
  summary?: string;
  rule_results: RuleResult[];
};
