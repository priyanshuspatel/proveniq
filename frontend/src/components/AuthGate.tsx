"use client";

import type { FormEvent, ReactNode } from "react";
import { useCallback, useEffect, useState } from "react";
import { Button, Card } from "@/components/ui";
import { authApi } from "@/lib/api";
import {
  AUTH_UNAUTHORIZED_EVENT,
  clearAccessCredential,
  readAccessCredential,
  writeAccessCredential,
} from "@/lib/auth";
import { authGateErrorMessage, isUnauthorized, type AuthGateStatus } from "@/lib/authGate";

type AuthGateProps = {
  children: ReactNode;
};

function AccessScreen({
  credential,
  error,
  status,
  onCredentialChange,
  onSubmit,
}: {
  credential: string;
  error: string | null;
  status: AuthGateStatus;
  onCredentialChange: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  const checking = status === "checking";

  return (
    <main className="mx-auto flex min-h-screen max-w-lg items-center px-4 py-10 sm:px-6">
      <Card className="w-full p-6 sm:p-8">
        <p className="eyebrow">Private workspace</p>
        <h1 className="text-3xl font-semibold tracking-tight">Access Proveniq</h1>
        <p className="mt-3 text-muted">
          Enter the operator access credential to open the local license desk.
        </p>
        <form className="mt-6 space-y-4" onSubmit={onSubmit}>
          <label className="block text-sm font-medium" htmlFor="access-credential">
            Access credential
            <input
              id="access-credential"
              className="field-control"
              type="password"
              value={credential}
              onChange={(event) => onCredentialChange(event.target.value)}
              autoComplete="current-password"
              aria-describedby={error ? "access-error" : "access-help"}
              disabled={checking}
              required
            />
          </label>
          <p id="access-help" className="text-sm text-muted">
            The credential is kept for this browser session only.
          </p>
          {error ? <p id="access-error" className="notice notice--error" role="alert">{error}</p> : null}
          <Button type="submit" disabled={checking} busy={checking} className="w-full">
            {checking ? "Verifying access…" : "Open workspace"}
          </Button>
        </form>
      </Card>
    </main>
  );
}

export default function AuthGate({ children }: AuthGateProps) {
  const [status, setStatus] = useState<AuthGateStatus>("checking");
  const [credential, setCredential] = useState("");
  const [error, setError] = useState<string | null>(null);

  const verifyCredential = useCallback(async () => {
    try {
      await authApi.verify();
      setError(null);
      setStatus("unlocked");
    } catch (verifyError) {
      if (isUnauthorized(verifyError)) {
        clearAccessCredential();
        setCredential("");
        setStatus("locked");
      } else {
        setStatus("error");
      }
      setError(authGateErrorMessage(verifyError));
    }
  }, []);

  useEffect(() => {
    const storedCredential = readAccessCredential();
    if (!storedCredential) {
      setStatus("locked");
      return;
    }
    setCredential(storedCredential);
    void verifyCredential();
  }, [verifyCredential]);

  useEffect(() => {
    function handleUnauthorized() {
      clearAccessCredential();
      setCredential("");
      setError("Your access credential is no longer valid. Enter it again to continue.");
      setStatus("locked");
    }

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
  }, []);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!credential.trim()) {
      setError("Enter an access credential.");
      setStatus("locked");
      return;
    }
    setError(null);
    setStatus("checking");
    writeAccessCredential(credential);
    void verifyCredential();
  }

  if (status !== "unlocked") {
    if (status === "checking" && !credential) {
      return <main className="mx-auto flex min-h-screen max-w-lg items-center px-4 py-10 sm:px-6" aria-live="polite"><p className="surface-card w-full px-4 py-6 text-muted" role="status">Checking access…</p></main>;
    }
    return (
      <AccessScreen
        credential={credential}
        error={error}
        status={status}
        onCredentialChange={(value) => {
          setCredential(value);
          if (error) setError(null);
        }}
        onSubmit={onSubmit}
      />
    );
  }

  return <>{children}</>;
}
