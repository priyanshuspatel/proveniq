import type { Metadata } from "next";
import { Fraunces, Source_Sans_3 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const sourceSans = Source_Sans_3({
  variable: "--font-source",
  subsets: ["latin"],
});

const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LicenseTrail",
  description: "Organize project assets and the license details a designer declared.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${sourceSans.variable} ${fraunces.variable} antialiased`}>
        <header className="border-b border-line bg-card">
          <div className="mx-auto flex max-w-6xl items-baseline justify-between px-6 py-5">
            <Link href="/" className="no-underline">
              <p className="font-serif text-2xl tracking-tight">LicenseTrail</p>
              <p className="text-sm text-muted">Proveniq handoff desk</p>
            </Link>
            <p className="max-w-sm text-right text-sm text-muted">
              Records what you declare. It does not decide legal compliance.
            </p>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
