import type { Metadata } from "next";
import Link from "next/link";
import { UserProvider } from "@auth0/nextjs-auth0/client";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AuthButton } from "@/components/AuthButton";
import "./globals.css";

export const metadata: Metadata = {
  title: "Builddy — AI App Builder powered by GLM 5.1",
  description: "Describe an app and GLM 5.1 plans, codes, reviews, and deploys it in minutes.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/* Inline script to prevent flash of wrong theme */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                var t = localStorage.getItem('builddy-theme');
                if (t === 'dark' || (!t && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                  document.documentElement.classList.add('dark');
                }
              })();
            `,
          }}
        />
      </head>
      <body className="min-h-screen antialiased">
        <UserProvider>
        {/* Bento-style nav */}
        <nav className="fixed top-0 left-0 right-0 z-40 border-b" style={{ background: 'var(--nav-bg)', borderColor: 'var(--nav-border)', backdropFilter: 'blur(20px) saturate(180%)', WebkitBackdropFilter: 'blur(20px) saturate(180%)' }}>
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-2.5 group">
              <img
                src="/logo.jpeg"
                alt="Builddy"
                className="h-8 w-8 rounded-xl object-cover shadow-sm transition-all group-hover:shadow-glow group-hover:scale-105"
              />
              <span className="text-lg font-display font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                Builddy
              </span>
            </Link>

            {/* Nav links */}
            <div className="flex items-center gap-1">
              {[
                { href: "/", label: "Dashboard" },
                { href: "/gallery", label: "Gallery" },
                { href: "/autopsy", label: "Code Autopsy" },
              ].map(({ href, label }) => (
                <Link
                  key={href}
                  href={href}
                  className="rounded-xl px-3.5 py-2 text-sm font-medium transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {label}
                </Link>
              ))}
            </div>

            {/* Right: auth + theme toggle + status */}
            <div className="flex items-center gap-3">
              <AuthButton />
              <ThemeToggle />
              <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                <span className="live-dot" />
                <span className="font-mono">GLM 5.1</span>
              </div>
            </div>
          </div>
        </nav>

        <main className="pt-14">{children}</main>
        </UserProvider>
      </body>
    </html>
  );
}
