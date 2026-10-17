import assert from "node:assert/strict";
import test from "node:test";
import { loadSavedReview, quotationsFromEvidence } from "./restore.ts";

test("restores quotations and does not treat a URL row as verified", () => {
  const rows = quotationsFromEvidence([
    {
      quotation: "licensed under CC-BY-4.0",
      verification_status: "verified",
      condition_type: "license-label",
    },
    {
      quotation: null,
      verification_status: "not-authenticated",
      condition_type: null,
    },
    {
      quotation: "invented",
      verification_status: "not-found",
      condition_type: "license-label",
    },
  ]);
  assert.equal(rows.length, 2);
  assert.equal(rows[0].verified, true);
  assert.equal(rows[1].verified, false);
  assert.equal(rows[1].verification_result, "not-found");
});

test("empty evidence stays empty", () => {
  assert.deepEqual(quotationsFromEvidence([]), []);
});

test("evidence API errors are not replaced with quotations", async () => {
  await assert.rejects(
    () =>
      loadSavedReview("asset", {
        evidence: async () => {
          throw new Error("Evidence could not be loaded.");
        },
        savedScreening: async () => ({ saved: false }),
        screen: async () => {
          throw new Error("screening should not run");
        },
      }),
    /Evidence could not be loaded/,
  );
});

test("reload reads the saved screening and does not post a new assessment", async () => {
  let posted = false;
  const loaded = await loadSavedReview("asset", {
    evidence: async () => [],
    savedScreening: async () => ({
      saved: true,
      outdated: false,
      review_status: "potential-conflict",
      summary: "A retained statement disagrees with another.",
      rule_results: [{ rule_id: "nc-vs-declared-use", outcome: "potential-conflict", explanation: "Commercial use conflicts." }],
    }),
    screen: async () => {
      posted = true;
      return {};
    },
  });
  assert.equal(posted, false);
  assert.equal(loaded.screening.saved, true);
  assert.equal(loaded.screening.rule_results?.[0].explanation, "Commercial use conflicts.");
});

test("a missing assessment is explicit", async () => {
  const loaded = await loadSavedReview("asset", {
    evidence: async () => [],
    savedScreening: async () => ({ saved: false, rule_results: [] }),
  });
  assert.equal(loaded.screening.saved, false);
  assert.equal(loaded.screening.review_status, undefined);
});

test("an outdated saved assessment stays available to display", async () => {
  const loaded = await loadSavedReview("asset", {
    evidence: async () => [],
    savedScreening: async () => ({
      saved: true,
      outdated: true,
      review_status: "potential-conflict",
      summary: "Previous result",
      rule_results: [{ rule_id: "project-vs-asset-intended-use", outcome: "potential-conflict", explanation: "Uses differ." }],
    }),
  });
  assert.equal(loaded.screening.outdated, true);
  assert.equal(loaded.screening.rule_results?.length, 1);
});
