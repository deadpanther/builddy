import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Builddy — AI App Builder powered by GLM 5.1",
  description: "Tweet @builddy to build an app. GLM 5.1 generates and deploys it instantly.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased" style={{ background: "#080808", color: "#e6edf3" }}>
        <nav className="fixed top-0 left-0 right-0 z-40 border-b border-neutral-800 bg-[#080808]/90 backdrop-blur-sm">
          <div className="mx-auto flex h-12 max-w-7xl items-center justify-between px-4">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2">
              <span className="rounded bg-violet-600 px-1.5 py-0.5 font-mono text-xs font-bold text-white">
                B
              </span>
              <span className="font-semibold text-neutral-100 tracking-tight">Builddy</span>
            </Link>

            {/* Nav links */}
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="rounded px-3 py-1.5 font-mono text-xs text-neutral-500 transition-colors hover:bg-neutral-800 hover:text-neutral-200"
              >
                Dashboard
              </Link>
              <Link
                href="/gallery"
                className="rounded px-3 py-1.5 font-mono text-xs text-neutral-500 transition-colors hover:bg-neutral-800 hover:text-neutral-200"
              >
                Gallery
              </Link>
              <Link
                href="/autopsy"
                className="rounded px-3 py-1.5 font-mono text-xs text-neutral-500 transition-colors hover:bg-neutral-800 hover:text-neutral-200"
              >
                Code Autopsy
              </Link>
            </div>

            {/* Status indicator */}
            <div className="flex items-center gap-2 font-mono text-[10px] text-neutral-600">
              <span className="live-dot" />
              <span>GLM 5.1 Online</span>
            </div>
          </div>
        </nav>

        <main className="pt-12">{children}</main>
      </body>
    </html>
  );
}
