import assert from "node:assert/strict";
import test from "node:test";
import {
  ACCESS_CREDENTIAL_KEY,
  authorizationValue,
  clearAccessCredential,
  readAccessCredential,
  requestHeaders,
  writeAccessCredential,
} from "./auth.ts";

function storage() {
  const values = new Map<string, string>();
  return {
    values,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  };
}

test("credential storage keeps only the entered credential in session storage", () => {
  const session = storage();
  writeAccessCredential("operator-secret", session);

  assert.equal(readAccessCredential(session), "operator-secret");
  assert.deepEqual([...session.values.entries()], [[ACCESS_CREDENTIAL_KEY, "operator-secret"]]);

  clearAccessCredential(session);
  assert.equal(readAccessCredential(session), null);
  assert.deepEqual([...session.values.entries()], []);
});

test("request headers use the entered credential as a Bearer token", () => {
  const headers = requestHeaders("operator-secret", { "X-Trace": "demo" }, true);

  assert.equal(authorizationValue("operator-secret"), "Bearer operator-secret");
  assert.equal(headers.get("Authorization"), "Bearer operator-secret");
  assert.equal(headers.get("Accept"), "application/json");
  assert.equal(headers.get("Content-Type"), "application/json");
  assert.equal(headers.get("X-Trace"), "demo");
});

test("request headers do not retain an authorization header without a credential", () => {
  const headers = requestHeaders(null, { Authorization: "Bearer stale" });

  assert.equal(headers.get("Authorization"), null);
});
