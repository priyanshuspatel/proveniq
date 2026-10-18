export function LoadingNote({ label }: { label: string }) {
  return (
    <p className="surface-card flex items-center gap-3 border-dashed px-4 py-6 text-muted" role="status" aria-live="polite">
      <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-indigo border-r-transparent" aria-hidden="true" />
      <span>{label}</span>
    </p>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="notice notice--error" role="alert">
      {message}
    </p>
  );
}

export function SuccessNote({ message }: { message: string }) {
  return (
    <p className="notice notice--success" role="status" aria-live="polite">
      {message}
    </p>
  );
}

export function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <div className="surface-card border-dashed px-5 py-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-prose text-muted">{body}</p>
    </div>
  );
}

export function FieldErrorText({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm font-medium text-red-800" role="alert">{message}</p>;
}
