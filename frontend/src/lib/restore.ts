export type StoredEvidence = {
  id?: string;
  quotation: string | null;
  verification_status: string;
  condition_type: string | null;
};

export type RestoredQuotation = {
  field: string;
  quotation: string;
  verification_result: string;
  verified: boolean;
};

export function quotationsFromEvidence(rows: StoredEvidence[]): RestoredQuotation[] {
  return rows
    .filter((row) => Boolean(row.quotation) && Boolean(row.condition_type))
    .map((row) => ({
      field: row.condition_type as string,
      quotation: row.quotation as string,
      verification_result: row.verification_status,
      verified: row.verification_status === "verified",
    }));
}

export type SavedScreening = {
  saved: boolean;
  outdated?: boolean;
  review_status?: string;
  summary?: string;
  rule_results?: { rule_id: string; outcome: string; explanation: string }[];
};

export async function loadSavedReview(
  assetId: string,
  api: {
    evidence: (id: string) => Promise<StoredEvidence[]>;
    savedScreening: (id: string) => Promise<SavedScreening>;
    screen?: (id: string) => Promise<unknown>;
  },
) {
  const [evidence, screening] = await Promise.all([api.evidence(assetId), api.savedScreening(assetId)]);
  return { evidence: quotationsFromEvidence(evidence), screening };
}
