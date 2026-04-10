import { Suspense } from "react";
import { EmbedForm } from "./EmbedForm";

export default function EmbedPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-[200px] bg-neutral-950 p-4 font-mono text-sm text-neutral-500">
          Loading…
        </div>
      }
    >
      <EmbedForm />
    </Suspense>
  );
}
