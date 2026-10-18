import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { ReviewStatus } from "@/lib/types";
import { reviewStatusLabel, reviewStatusTone } from "@/lib/types";

type ButtonVariant = "primary" | "secondary" | "danger" | "dark";

const buttonVariants: Record<ButtonVariant, string> = {
  primary: "bg-indigo text-white shadow-sm hover:bg-indigo-700",
  secondary: "border border-line bg-card text-ink hover:border-indigo hover:text-indigo",
  danger: "border border-red-300 bg-card text-red-900 hover:bg-red-50",
  dark: "bg-stone-900 text-white hover:bg-stone-800",
};

export function Button({ variant = "primary", busy = false, children, className = "", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; busy?: boolean }) {
  return (
    <button
      {...props}
      className={`inline-flex min-h-10 items-center justify-center rounded-lg px-4 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${buttonVariants[variant]} ${className}`}
    >
      {busy ? <span className="mr-2 inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`surface-card ${className}`}>{children}</section>;
}

export function StatusBadge({ status, label }: { status: ReviewStatus | null | undefined; label?: string }) {
  const text = label ?? (status ? reviewStatusLabel(status) : "Not assessed");
  const tone = reviewStatusTone(status);
  const toneClasses = {
    teal: "status-badge--teal",
    amber: "status-badge--amber",
    red: "status-badge--red",
    neutral: "status-badge--neutral",
  };
  const symbol = tone === "teal" ? "✓" : tone === "red" ? "!" : tone === "amber" ? "•" : "–";
  return (
    <span className={`status-badge ${toneClasses[tone]}`}>
      <span aria-hidden="true" className="status-badge__symbol">{symbol}</span>
      <span>{text}</span>
    </span>
  );
}

export function SectionHeading({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div>
        {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description ? <p className="mt-1 max-w-2xl text-sm text-muted">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}
