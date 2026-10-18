export const ACCESS_CREDENTIAL_KEY = "proveniq.accessCredential";
export const AUTH_UNAUTHORIZED_EVENT = "proveniq:auth-unauthorized";

export type CredentialStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

function browserSessionStorage(): CredentialStorage | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage;
}

export function readAccessCredential(storage: CredentialStorage | null = browserSessionStorage()): string | null {
  if (!storage) return null;
  const credential = storage.getItem(ACCESS_CREDENTIAL_KEY);
  return credential || null;
}

export function writeAccessCredential(credential: string, storage: CredentialStorage | null = browserSessionStorage()): void {
  storage?.setItem(ACCESS_CREDENTIAL_KEY, credential);
}

export function clearAccessCredential(storage: CredentialStorage | null = browserSessionStorage()): void {
  storage?.removeItem(ACCESS_CREDENTIAL_KEY);
}

export function authorizationValue(credential: string): string {
  return `Bearer ${credential}`;
}

export function requestHeaders(
  credential: string | null,
  headers?: HeadersInit,
  hasBody = false,
): Headers {
  const result = new Headers(headers);
  result.set("Accept", "application/json");
  if (hasBody) result.set("Content-Type", "application/json");
  if (credential) result.set("Authorization", authorizationValue(credential));
  else result.delete("Authorization");
  return result;
}
