export type AuthGateStatus = "checking" | "locked" | "unlocked" | "error";

export function isUnauthorized(error: unknown): boolean {
  return typeof error === "object" && error !== null && "status" in error && error.status === 401;
}

export function authGateErrorMessage(error: unknown): string {
  if (isUnauthorized(error)) return "That access credential was not accepted.";
  if (error instanceof Error && error.message) return error.message;
  return "The access credential could not be verified. Try again.";
}
