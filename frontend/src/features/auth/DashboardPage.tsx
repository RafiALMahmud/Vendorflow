import { useAuth } from "./useAuth";

export function DashboardPage() {
  const { user, logout } = useAuth();

  return (
    <main className="mx-auto max-w-4xl px-6 py-14">
      <section className="rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-cyan-400">
          Protected vendor area
        </p>
        <h1 className="mt-3 text-3xl font-bold">Hello, {user?.full_name}</h1>
        <dl className="mt-8 grid gap-4 rounded-2xl bg-slate-950 p-5 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-slate-500">Email</dt>
            <dd className="mt-1 text-slate-200">{user?.email}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-500">Role</dt>
            <dd className="mt-1 capitalize text-slate-200">{user?.role}</dd>
          </div>
        </dl>
        <button
          className="mt-8 rounded-xl border border-slate-700 px-4 py-2 text-sm hover:border-slate-500"
          onClick={logout}
          type="button"
        >
          Log out
        </button>
      </section>
    </main>
  );
}
