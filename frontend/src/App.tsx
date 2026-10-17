import { useEffect, useState } from "react";

import { getHealth, type HealthResponse } from "./shared/api";

type HealthState =
  | { kind: "loading" }
  | { kind: "online"; data: HealthResponse }
  | { kind: "offline" };

function App() {
  const [health, setHealth] = useState<HealthState>({ kind: "loading" });

  useEffect(() => {
    const controller = new AbortController();

    getHealth(controller.signal)
      .then((data) => setHealth({ kind: "online", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setHealth({ kind: "offline" });
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <section className="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">
        <div className="grid gap-10 p-8 md:grid-cols-[1.4fr_1fr] md:p-12">
          <div>
            <p className="mb-4 text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
              Vendor onboarding, made reviewable
            </p>
            <h1 className="text-4xl font-bold tracking-tight md:text-6xl">
              VendorFlow AI
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              A secure workspace for collecting vendor documents, reviewing
              extracted fields, and making transparent human decisions.
            </p>
          </div>

          <aside className="rounded-2xl bg-slate-800/70 p-6" aria-live="polite">
            <p className="text-sm font-medium text-slate-400">API connection</p>
            {health.kind === "loading" && (
              <p className="mt-3 text-lg">Checking backend…</p>
            )}
            {health.kind === "online" && (
              <div className="mt-3">
                <p className="text-lg font-semibold text-emerald-400">
                  Backend online
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  {health.data.service} · {health.data.environment}
                </p>
              </div>
            )}
            {health.kind === "offline" && (
              <div className="mt-3">
                <p className="text-lg font-semibold text-amber-400">
                  Backend unavailable
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  Start FastAPI on port 8000, then refresh this page.
                </p>
              </div>
            )}
          </aside>
        </div>
      </section>
    </main>
  );
}

export default App;

