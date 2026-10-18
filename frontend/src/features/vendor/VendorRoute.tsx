import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../auth/useAuth";

export function VendorRoute() {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (user.role !== "vendor") {
    return (
      <main className="mx-auto max-w-3xl px-6 py-14">
        <section className="rounded-3xl border border-rose-900/70 bg-slate-900 p-8">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-rose-300">
            Forbidden
          </p>
          <h1 className="mt-3 text-3xl font-bold">Vendor access required</h1>
          <p className="mt-3 text-slate-400">
            This workspace is available only to authenticated vendor accounts.
          </p>
        </section>
      </main>
    );
  }

  return <Outlet />;
}
