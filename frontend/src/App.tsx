import { useEffect, useState } from "react";
import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./features/auth/AuthProvider";
import { LoginPage } from "./features/auth/LoginPage";
import { ProtectedRoute } from "./features/auth/ProtectedRoute";
import { RegisterPage } from "./features/auth/RegisterPage";
import { useAuth } from "./features/auth/useAuth";
import { DocumentsPage } from "./features/vendor/DocumentsPage";
import { DocumentDetailPage } from "./features/vendor/DocumentDetailPage";
import { ExtractionReviewPage } from "./features/vendor/ExtractionReviewPage";
import { VendorDashboardPage } from "./features/vendor/VendorDashboardPage";
import { VendorProfilePage } from "./features/vendor/VendorProfilePage";
import { VendorRoute } from "./features/vendor/VendorRoute";
import { ApplicationsPage } from "./features/applications/ApplicationsPage";
import { AdminPage } from "./features/admin/AdminPage";
import { getHealth, type HealthResponse } from "./shared/api";

type HealthState =
  | { kind: "loading" }
  | { kind: "online"; data: HealthResponse }
  | { kind: "offline" };

function HomePage() {
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
    <main className="mx-auto max-w-5xl px-6 py-16">
      <section className="overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">
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
            <div className="mt-8 flex gap-3">
              <Link className="primary-button" to="/register">
                Create vendor account
              </Link>
              <Link className="secondary-button" to="/login">
                Sign in
              </Link>
            </div>
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

function Navigation() {
  const { user, logout } = useAuth();

  return (
    <header className="border-b border-slate-800 bg-slate-950/90">
      <nav
        className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-4 px-6 py-4 sm:flex-row sm:items-center"
        aria-label="Primary navigation"
      >
        <Link className="font-bold tracking-tight" to="/">
          VendorFlow AI
        </Link>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {user ? (
            <>
              {user.role === "vendor" && (
                <>
                  <Link className="text-slate-300 hover:text-white" to="/dashboard">
                    Dashboard
                  </Link>
                  <Link className="text-slate-300 hover:text-white" to="/profile">
                    Company profile
                  </Link>
                  <Link className="text-slate-300 hover:text-white" to="/documents">
                    Documents
                  </Link>
                  <Link className="text-cyan-300 hover:text-white" to="/applications">Applications</Link>
                </>
              )}
              {user.role === "admin" && <Link className="text-cyan-300" to="/admin">Admin reviews</Link>}
              <button
                className="text-slate-300 hover:text-white"
                onClick={logout}
                type="button"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link className="text-slate-300 hover:text-white" to="/login">
                Sign in
              </Link>
              <Link className="text-cyan-300 hover:text-cyan-200" to="/register">
                Register
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}

export function AppRoutes() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Navigation />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/dashboard" element={<RoleDashboard />} />
          <Route element={<VendorRoute />}>
            <Route path="/applications" element={<ApplicationsPage />} />
            <Route path="/profile" element={<VendorProfilePage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/documents/:documentId" element={<DocumentDetailPage />} />
            <Route
              path="/documents/:documentId/review"
              element={<ExtractionReviewPage />}
            />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

function RoleDashboard() {
  const { user } = useAuth();
  return user?.role === 'admin' ? <Navigate to="/admin" replace /> : <VendorDashboardPage />;
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;

