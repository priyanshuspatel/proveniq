import assert from "node:assert/strict";
import test from "node:test";
import { filterProjects } from "./projectFilters.ts";
import { reviewStatusTone, type Project } from "./types.ts";

const projects: Project[] = [
  { id: "1", name: "Brand refresh", client_label: "Acme", declared_intended_use: "commercial", created_at: "2026-01-01", asset_count: 4, review_status: "supported-checks-passed" },
  { id: "2", name: "Editorial kit", client_label: "Northwind", declared_intended_use: "noncommercial", created_at: "2026-01-02", asset_count: 1, review_status: "potential-conflict" },
];

test("project search matches project and client labels", () => {
  assert.deepEqual(filterProjects(projects, "north", "all").map((project) => project.id), ["2"]);
});

test("needs-review excludes only projects with a passed review", () => {
  assert.deepEqual(filterProjects(projects, "", "needs-review").map((project) => project.id), ["2"]);
});

test("empty search keeps all projects", () => {
  assert.equal(filterProjects(projects, "  ", "all").length, 2);
});

test("status tones keep review meaning available beyond color", () => {
  assert.equal(reviewStatusTone("supported-checks-passed"), "teal");
  assert.equal(reviewStatusTone("potential-conflict"), "amber");
  assert.equal(reviewStatusTone("manual-review-required"), "red");
  assert.equal(reviewStatusTone(null), "neutral");
});
