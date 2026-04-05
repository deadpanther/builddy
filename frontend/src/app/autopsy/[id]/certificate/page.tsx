"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { getCertificate } from "@/lib/api";
import type { Certificate } from "@/lib/types";

export default function CertificatePage() {
  const { id } = useParams<{ id: string }>();
  const [cert, setCert] = useState<Certificate | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getCertificate(id)
      .then(setCert)
      .catch(() => setError("Certificate not ready or autopsy not found."));
  }, [id]);

  if (error) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] items-center justify-center px-4">
        <div className="text-center">
          <p className="font-typewriter text-sm text-terminal-red">{error}</p>
          <a href={`/autopsy/${id}`} className="mt-3 inline-block font-mono text-xs text-evidence-blue hover:underline">
            &larr; Back to case file
          </a>
        </div>
      </div>
    );
  }

  if (!cert) {
    return (
      <div className="flex min-h-[calc(100vh-48px)] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-terminal-green border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-48px)] items-center justify-center px-4 py-12">
      <div className="certificate-border w-full max-w-2xl bg-[#0c0c0c] p-10">
        {/* Header Ornament */}
        <div className="mb-6 flex justify-center">
          <div className="flex items-center gap-4 text-neutral-600">
            <span className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent w-16" />
            <span className="font-serif text-lg tracking-[0.3em] uppercase text-neutral-500">
              Official Record
            </span>
            <span className="h-px flex-1 bg-gradient-to-l from-transparent via-neutral-700 to-transparent w-16" />
          </div>
        </div>

        {/* Title */}
        <div className="mb-8 text-center">
          <h1 className="font-serif text-4xl font-bold tracking-wide text-neutral-100">
            Certificate of Death
          </h1>
          <p className="mt-1 font-serif text-sm italic text-neutral-500">
            Software Repository &mdash; Forensic Examination Report
          </p>
        </div>

        {/* Certificate Number */}
        <div className="mb-8 text-center">
          <span className="rounded border border-autopsy-border px-4 py-1.5 font-mono text-xs tracking-[0.3em] text-neutral-500">
            CERT NO. {cert.certificate_number}
          </span>
        </div>

        {/* Fields */}
        <div className="space-y-5 mb-8">
          <CertField label="Name of Deceased" value={cert.repository} highlight />
          <CertField label="Repository URL" value={cert.repository_url} mono />

          <div className="grid grid-cols-2 gap-4">
            <CertField label="Date of Birth (First Commit)" value={cert.date_of_birth} />
            <CertField label="Date of Death (Last Activity)" value={cert.date_of_death} />
          </div>

          <div className="rounded border-2 border-terminal-red/20 bg-terminal-red/5 px-5 py-4">
            <div className="mb-1 font-serif text-[10px] uppercase tracking-[0.2em] text-terminal-red">
              Cause of Death
            </div>
            <p className="font-serif text-lg leading-relaxed text-neutral-100">
              {cert.cause_of_death}
            </p>
          </div>

          {cert.contributing_factors.length > 0 && (
            <div>
              <div className="mb-2 font-serif text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                Contributing Factors
              </div>
              <ul className="space-y-1">
                {cert.contributing_factors.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-neutral-300">
                    <span className="mt-1 text-neutral-600">&bull;</span>
                    <span className="font-serif">{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {cert.lessons.length > 0 && (
            <div>
              <div className="mb-2 font-serif text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                Recommendations for Prevention
              </div>
              <ul className="space-y-1">
                {cert.lessons.map((l, i) => (
                  <li key={i} className="text-xs text-neutral-400 font-serif leading-relaxed">
                    {i + 1}. {l}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Separator */}
        <div className="mb-6 flex items-center gap-4 text-neutral-700">
          <span className="h-px flex-1 bg-gradient-to-r from-transparent via-neutral-700 to-transparent" />
          <span className="text-xs tracking-[0.3em]">&#x2020;</span>
          <span className="h-px flex-1 bg-gradient-to-l from-transparent via-neutral-700 to-transparent" />
        </div>

        {/* Signature */}
        <div className="flex items-end justify-between">
          <div>
            <div className="mb-1 font-serif text-[10px] uppercase tracking-[0.2em] text-neutral-600">
              Examining Pathologist
            </div>
            <div className="font-serif text-xl italic text-terminal-green">
              {cert.examining_pathologist}
            </div>
            <div className="mt-0.5 h-px w-48 bg-neutral-700" />
            <div className="mt-1 font-mono text-[10px] text-neutral-600">
              Zhipu AI Forensic Laboratory
            </div>
          </div>

          <div className="text-right">
            <div className="mb-1 font-serif text-[10px] uppercase tracking-[0.2em] text-neutral-600">
              Date of Examination
            </div>
            <div className="font-mono text-sm text-neutral-400">
              {cert.date_of_examination
                ? new Date(cert.date_of_examination).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })
                : "Unknown"}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center font-mono text-[9px] tracking-[0.2em] text-neutral-700 uppercase">
          This document was generated by automated forensic analysis and is provided for informational purposes only.
        </div>
      </div>

      {/* Actions below certificate */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 flex gap-3">
        <a
          href={`/autopsy/${id}`}
          className="rounded border border-autopsy-border bg-autopsy-surface px-4 py-2 font-mono text-xs text-neutral-400 transition-colors hover:border-autopsy-border-light hover:text-neutral-200"
        >
          &larr; Full Report
        </a>
        <button
          onClick={() => window.print()}
          className="rounded border border-terminal-green/30 bg-terminal-green/5 px-4 py-2 font-mono text-xs text-terminal-green transition-colors hover:bg-terminal-green/10"
        >
          Print Certificate
        </button>
      </div>
    </div>
  );
}

function CertField({
  label,
  value,
  highlight,
  mono,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  mono?: boolean;
}) {
  return (
    <div>
      <div className="mb-1 font-serif text-[10px] uppercase tracking-[0.2em] text-neutral-500">
        {label}
      </div>
      <div
        className={`border-b border-dashed border-autopsy-border pb-1 ${
          highlight
            ? "font-serif text-2xl font-bold text-neutral-100"
            : mono
              ? "font-mono text-sm text-evidence-blue"
              : "font-serif text-sm text-neutral-300"
        }`}
      >
        {value || "Unknown"}
      </div>
    </div>
  );
}
