export function LoadingNote({ label }: { label: string }) {
  return (
    <p className="rounded-lg border border-dashed border-line bg-card px-4 py-6 text-muted" role="status">
      {label}
    </p>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-red-900" role="alert">
      {message}
    </p>
  );
}

export function SuccessNote({ message }: { message: string }) {
  return (
    <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-950" role="status">
      {message}
    </p>
  );
}

export function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-card px-5 py-8">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 max-w-prose text-muted">{body}</p>
    </div>
  );
}

export function FieldErrorText({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm text-red-800">{message}</p>;
}
