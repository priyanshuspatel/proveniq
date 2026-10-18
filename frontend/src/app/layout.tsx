import type { Metadata } from "next";
import { Source_Sans_3 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Proveniq",
  description: "Local desk for declared asset licenses. Not a legal clearance.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sourceSans.variable} antialiased`}>
        <header className="no-print border-b border-line bg-card">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-5">
            <Link href="/" className="no-underline">
              <p className="text-xl font-semibold tracking-tight">Proveniq</p>
              <p className="text-sm text-muted">Local license desk</p>
            </Link>
            <p className="max-w-xs text-right text-sm text-muted">
              Records declarations and checked quotations. Not a legal clearance.
            </p>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      </body>
    </html>
  );
}
