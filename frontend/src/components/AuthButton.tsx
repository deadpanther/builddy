"use client";

import Link from "next/link";
import { useUser } from "@auth0/nextjs-auth0/client";
import { LogIn, LogOut, User } from "lucide-react";

export function AuthButton() {
  const { user, isLoading } = useUser();

  if (isLoading) {
    return (
      <div className="h-8 w-8 animate-pulse rounded-full bg-surface-100" />
    );
  }

  if (user) {
    return (
      <div className="flex items-center gap-2.5">
        <Link
          href="/profile"
          className="flex items-center gap-2 rounded-xl border border-stroke bg-surface-100 px-2.5 py-1.5 transition-colors hover:bg-surface-200"
        >
          {user.picture ? (
            <img
              src={user.picture}
              alt={user.name ?? "User"}
              className="h-5 w-5 rounded-full"
            />
          ) : (
            <User className="h-4 w-4 text-brand-400" />
          )}
          <span className="max-w-[100px] truncate text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            {user.name ?? user.email}
          </span>
        </Link>
        <a
          href="/api/auth/logout"
          className="flex items-center gap-1.5 rounded-xl border border-stroke bg-surface-100 px-2.5 py-1.5 text-xs font-medium transition-colors hover:bg-surface-200"
          style={{ color: 'var(--text-secondary)' }}
        >
          <LogOut className="h-3.5 w-3.5" />
          Logout
        </a>
      </div>
    );
  }

  return (
    <a
      href="/api/auth/login"
      className="flex items-center gap-1.5 rounded-xl border border-brand-500/30 bg-brand-500/15 px-3 py-1.5 text-xs font-semibold text-brand-300 transition-all hover:bg-brand-500/25 hover:shadow-glow"
    >
      <LogIn className="h-3.5 w-3.5" />
      Sign In
    </a>
  );
}
