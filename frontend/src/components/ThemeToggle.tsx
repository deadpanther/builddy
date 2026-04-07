"use client";

import { useState, useEffect } from "react";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("builddy-theme", next ? "dark" : "light");
  };

  if (!mounted) return <div className="h-8 w-8" />;

  return (
    <button
      onClick={toggle}
      className="flex h-8 w-8 items-center justify-center rounded-xl transition-colors hover:bg-black/5 dark:hover:bg-white/5"
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? (
        <Sun className="h-4 w-4 text-amber-400" />
      ) : (
        <Moon className="h-4 w-4 text-stone-500" />
      )}
    </button>
  );
}
