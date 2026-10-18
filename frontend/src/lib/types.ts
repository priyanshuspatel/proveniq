export type IntendedUse =
  | "client-delivery-as-is"
  | "client-delivery-modified"
  | "commercial"
  | "noncommercial";

export type ReviewStatus =
  | "supported-checks-passed"
  | "potential-conflict"
  | "missing-information"
  | "unsupported-license"
  | "manual-review-required";

export type Project = {
  id: string;
  name: string;
  client_label: string | null;
  declared_intended_use: IntendedUse;
  created_at: string;
  /** Populated by newer API versions; optional for older projects. */
  asset_count?: number;
  review_status?: ReviewStatus | null;
};

export type Asset = {
  id: string;
  project_id: string;
  title: string;
  creator: string | null;
  source_url: string | null;
  declared_license: string;
  supplied_license_text: string | null;
  intended_use: IntendedUse | null;
  attribution_text: string | null;
  review_status: ReviewStatus;
};

export type FieldError = {
  loc: string;
  message: string;
};

export const INTENDED_USES: { value: IntendedUse; label: string }[] = [
  { value: "client-delivery-as-is", label: "Client delivery, as is" },
  { value: "client-delivery-modified", label: "Client delivery, modified" },
  { value: "commercial", label: "Commercial" },
  { value: "noncommercial", label: "Noncommercial" },
];

export function intendedUseLabel(value: IntendedUse | null): string {
  if (!value) return "Not declared";
  return INTENDED_USES.find((item) => item.value === value)?.label ?? value;
}

export function reviewStatusLabel(value: ReviewStatus): string {
  const labels: Record<ReviewStatus, string> = {
    "supported-checks-passed": "Supported checks passed",
    "potential-conflict": "Potential conflict",
    "missing-information": "Missing information",
    "unsupported-license": "Unsupported license",
    "manual-review-required": "Manual review required",
  };
  return labels[value];
}

export function reviewStatusTone(value: ReviewStatus | null | undefined): "teal" | "amber" | "red" | "neutral" {
  if (value === "supported-checks-passed") return "teal";
  if (value === "potential-conflict" || value === "missing-information") return "amber";
  if (value === "unsupported-license" || value === "manual-review-required") return "red";
  return "neutral";
}
