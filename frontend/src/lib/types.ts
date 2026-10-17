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
  return value.replaceAll("-", " ");
}
