import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import {
  ApiError,
  getVendorProfile,
  listDocuments,
  type VendorDocument,
  type VendorProfile,
} from "../../shared/api";
import { useAuth } from "../auth/useAuth";

type DashboardState =
  | { kind: "loading" }
  | {
      kind: "ready";
      profile: VendorProfile | null;
      documents: VendorDocument[];
    }
  | { kind: "error"; message: string; forbidden: boolean };

function dashboardError(error: unknown) {
  if (error instanceof ApiError) {
    return {
      message:
        error.status === 403
          ? "Your account cannot access the vendor workspace."
          : error.detail,
      forbidden: error.status === 403,
    };
  }
  return {
    message: "Network error. Check that the backend is running, then retry.",
    forbidden: false,
  };
}

export function VendorDashboardPage() {
  const { token, user } = useAuth();
  const [state, setState] = useState<DashboardState>({ kind: "loading" });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!token) return;
    let active = true;

    async function loadDashboard() {
      setState({ kind: "loading" });
      try {
        let profile: VendorProfile | null = null;
        try {
          profile = await getVendorProfile(token as string);
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 404)) throw error;
        }
        const documents = await listDocuments(token as string);
        if (active) setState({ kind: "ready", profile, documents });
      } catch (error) {
        if (active) setState({ kind: "error", ...dashboardError(error) });
      }
    }

    void loadDashboard();
    return () => {
      active = false;
    };
  }, [reloadKey, token]);

  if (state.kind === "loading") {
    return (
      <main className="mx-auto max-w-5xl px-6 py-14" aria-live="polite">
        <p className="text-slate-300">Loading your vendor workspace…</p>
      </main>
    );
  }

  if (state.kind === "error") {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <section className="rounded-3xl border border-rose-900/70 bg-slate-900 p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-300">
            {state.forbidden ? "Forbidden" : "Connection problem"}
          </p>
          <h1 className="mt-3 text-3xl font-bold">Unable to load dashboard</h1>
          <p className="mt-3 text-slate-300" role="alert">
            {state.message}
          </p>
          {!state.forbidden && (
            <button
              className="primary-button mt-6"
              type="button"
              onClick={() => setReloadKey((key) => key + 1)}
            >
              Retry
            </button>
          )}
        </section>
      </main>
    );
  }

  const processed = state.documents.filter(
    (document) => document.processing_status === "processed",
  ).length;
  const failed = state.documents.filter(
    (document) => document.processing_status === "failed",
  ).length;

  return (
    <main className="mx-auto max-w-5xl px-6 py-14">
      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-6 shadow-2xl sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Vendor workspace
        </p>
        <h1 className="mt-3 text-3xl font-bold">Welcome, {user?.full_name}</h1>
        <p className="mt-2 text-slate-400">
          Complete your company information, upload documents, and verify extraction results.
        </p>

        <dl className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Company profile" value={state.profile ? "Complete" : "Not set up"} />
          <Metric label="Documents" value={String(state.documents.length)} />
          <Metric label="Processed" value={String(processed)} />
          <Metric
            label="Failed"
            value={String(failed)}
            tone={failed ? "warning" : "normal"}
          />
        </dl>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <DashboardAction
            title={state.profile ? state.profile.company_name : "Create company profile"}
            description={
              state.profile
                ? `Registration ${state.profile.registration_number}`
                : "A profile is required before document upload."
            }
            href="/profile"
            action={state.profile ? "Edit profile" : "Set up profile"}
          />
          <DashboardAction
            title="Vendor documents"
            description={
              state.documents.length
                ? `${state.documents.length} document${state.documents.length === 1 ? "" : "s"} stored privately.`
                : "No documents uploaded yet."
            }
            href="/documents"
            action="Manage documents"
          />
        </div>
      </section>

      <section className="mt-8 rounded-3xl border border-dashed border-slate-700 bg-slate-900/60 p-6 sm:p-8">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-400">
          Application status
        </p>
        <h2 className="mt-3 text-xl font-semibold">Integration pending</h2>
        <p className="mt-2 text-slate-400">
          Developer 2's application/status route is not present on this branch. No submission
          state is being simulated.
        </p>
      </section>
    </main>
  );
}

function Metric({
  label,
  value,
  tone = "normal",
}: {
  label: string;
  value: string;
  tone?: "normal" | "warning";
}) {
  return (
    <div className="rounded-2xl bg-slate-950 p-5">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd
        className={`mt-2 text-2xl font-bold ${tone === "warning" ? "text-amber-300" : "text-slate-100"}`}
      >
        {value}
      </dd>
    </div>
  );
}

function DashboardAction({
  title,
  description,
  href,
  action,
}: {
  title: string;
  description: string;
  href: string;
  action: string;
}) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-950 p-5">
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 min-h-12 text-sm text-slate-400">{description}</p>
      <Link className="secondary-button mt-5 text-sm" to={href}>
        {action}
      </Link>
    </article>
  );
}
