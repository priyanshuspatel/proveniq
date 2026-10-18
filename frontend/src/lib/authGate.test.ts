import assert from "node:assert/strict";
import test from "node:test";
import { authGateErrorMessage, isUnauthorized } from "./authGate.ts";

test("auth gate identifies expired or rejected credentials", () => {
  assert.equal(isUnauthorized({ status: 401 }), true);
  assert.equal(isUnauthorized({ status: 403 }), false);
  assert.equal(authGateErrorMessage({ status: 401 }), "That access credential was not accepted.");
});

test("auth gate preserves useful verification errors", () => {
  assert.equal(authGateErrorMessage(new Error("The API could not be reached.")), "The API could not be reached.");
  assert.equal(authGateErrorMessage("unknown"), "The access credential could not be verified. Try again.");
});
