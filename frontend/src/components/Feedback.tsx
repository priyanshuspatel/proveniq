export function LoadingNote({ label }: { label: string }) {
  return (
    <p className="rounded-md border border-dashed border-line bg-card px-4 py-6 text-muted" role="status">
      {label}
    </p>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-clay/30 bg-white px-4 py-3 text-clay-deep" role="alert">
      {message}
    </p>
  );
}

export function SuccessNote({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-ok/30 bg-white px-4 py-3 text-ok" role="status">
      {message}
    </p>
  );
}

export function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md border border-dashed border-line bg-card px-5 py-8">
      <h2 className="font-serif text-xl">{title}</h2>
      <p className="mt-2 max-w-prose text-muted">{body}</p>
    </div>
  );
}

export function FieldErrorText({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-sm text-clay">{message}</p>;
}
