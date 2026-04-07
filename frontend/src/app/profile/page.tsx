"use client";

export const dynamic = "force-dynamic";

import { useUser } from "@auth0/nextjs-auth0/client";
import { User, Mail, Clock, Shield, LogIn } from "lucide-react";
import Link from "next/link";

export default function ProfilePage() {
  const { user, isLoading, error } = useUser();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20">
        <div className="glass-panel p-10 flex flex-col items-center gap-4">
          <div className="h-20 w-20 animate-pulse rounded-full bg-surface-100" />
          <div className="h-4 w-48 animate-pulse rounded bg-surface-100" />
          <div className="h-3 w-32 animate-pulse rounded bg-surface-100" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20">
        <div className="glass-panel p-10 text-center">
          <p className="text-danger text-sm">{error.message}</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20">
        <div className="glass-panel p-10 flex flex-col items-center gap-5">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-500/15">
            <User className="h-8 w-8 text-brand-400" />
          </div>
          <h1 className="text-xl font-display font-semibold" style={{ color: "var(--text-primary)" }}>
            Sign in to view your profile
          </h1>
          <p className="text-sm text-center" style={{ color: "var(--text-tertiary)" }}>
            Authenticate with Auth0 to see your profile details
          </p>
          <a
            href="/api/auth/login"
            className="flex items-center gap-2 rounded-xl border border-brand-500/30 bg-brand-500/20 px-5 py-2.5 text-sm font-semibold text-brand-300 transition-all hover:bg-brand-500/30 hover:shadow-glow"
          >
            <LogIn className="h-4 w-4" />
            Sign In with Auth0
          </a>
        </div>
      </div>
    );
  }

  const infoItems = [
    { icon: User, label: "Name", value: user.name ?? "—" },
    { icon: Mail, label: "Email", value: user.email ?? "—", verified: user.email_verified },
    { icon: Shield, label: "Auth Provider", value: user.sub?.split("|")[0] ?? "auth0" },
    {
      icon: Clock,
      label: "Last Updated",
      value: user.updated_at
        ? new Date(user.updated_at as string).toLocaleDateString("en-US", {
            year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit",
          })
        : "—",
    },
  ];

  return (
    <div className="mx-auto max-w-2xl px-6 py-20">
      <div className="glass-panel overflow-hidden">
        {/* Header with avatar */}
        <div className="relative flex flex-col items-center px-6 pt-10 pb-6" style={{ background: "linear-gradient(135deg, var(--brand-500-15) 0%, transparent 60%)" }}>
          {user.picture ? (
            <img
              src={user.picture}
              alt={user.name ?? "User"}
              className="h-24 w-24 rounded-full border-4 shadow-lg"
              style={{ borderColor: "var(--brand-500)" }}
            />
          ) : (
            <div className="flex h-24 w-24 items-center justify-center rounded-full bg-brand-500/20 border-4" style={{ borderColor: "var(--brand-500)" }}>
              <User className="h-12 w-12 text-brand-400" />
            </div>
          )}
          <h1 className="mt-4 text-2xl font-display font-bold" style={{ color: "var(--text-primary)" }}>
            {user.name ?? "User"}
          </h1>
          {user.nickname && (
            <p className="mt-1 font-mono text-sm" style={{ color: "var(--text-tertiary)" }}>
              @{user.nickname}
            </p>
          )}
        </div>

        {/* Info cards */}
        <div className="p-6 space-y-3">
          {infoItems.map(({ icon: Icon, label, value, verified }) => (
            <div
              key={label}
              className="flex items-center gap-4 rounded-xl border px-4 py-3 transition-colors"
              style={{ borderColor: "var(--stroke)", background: "var(--surface-100)" }}
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500/10">
                <Icon className="h-4 w-4 text-brand-400" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-mono text-[10px] uppercase tracking-wider" style={{ color: "var(--text-tertiary)" }}>
                  {label}
                </p>
                <p className="truncate text-sm font-medium" style={{ color: "var(--text-primary)" }}>
                  {value}
                </p>
              </div>
              {verified !== undefined && (
                <span
                  className={`rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold ${
                    verified
                      ? "bg-success-dim text-success border border-success-border"
                      : "bg-warning-dim text-warning border border-warning-border"
                  }`}
                >
                  {verified ? "Verified" : "Unverified"}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="border-t px-6 py-4 flex items-center justify-between" style={{ borderColor: "var(--stroke)" }}>
          <p className="font-mono text-[10px]" style={{ color: "var(--text-tertiary)" }}>
            Powered by Auth0
          </p>
          <div className="flex gap-2">
            <Link
              href="/"
              className="rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors hover:bg-surface-200"
              style={{ borderColor: "var(--stroke)", color: "var(--text-secondary)" }}
            >
              Back to Dashboard
            </Link>
            <a
              href="/api/auth/logout"
              className="rounded-lg border border-danger-border bg-danger-dim px-3 py-1.5 text-xs font-medium text-danger transition-colors hover:bg-danger/20"
            >
              Sign Out
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
