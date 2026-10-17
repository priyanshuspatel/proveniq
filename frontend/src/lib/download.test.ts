import assert from "node:assert/strict";
import test from "node:test";
import { reportFilename, saveGeneratedReport } from "./download.ts";

test("does not report success when the report body is missing", async () => {
  let writes = 0;
  await assert.rejects(
    () => saveGeneratedReport("  ", reportFilename("project", 1), async () => {
      writes += 1;
      return true;
    }),
    /not generated/,
  );
  assert.equal(writes, 0);
});

test("does not report success when the file is not saved", async () => {
  await assert.rejects(
    () => saveGeneratedReport("# checklist\n", "proveniq-project-v1.md", async () => false),
    /not saved/,
  );
});

test("returns the filename only after the file write succeeds", async () => {
  let written = "";
  const filename = await saveGeneratedReport("# checklist\n", reportFilename("abc", 2), async (name, markdown) => {
    written = `${name}\n${markdown}`;
    return true;
  });
  assert.equal(filename, "proveniq-abc-v2.md");
  assert.match(written, /checklist/);
});
