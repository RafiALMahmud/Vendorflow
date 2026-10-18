import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { apiRequest } from '../../shared/api';
import { useAuth } from '../auth/useAuth';
import { ApplicationStatus } from './ApplicationStatus';
import type { Application } from './types';

export function ApplicationsPage() {
  const { token } = useAuth();
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    apiRequest<Application[]>('/applications/me', { token: token ?? '', signal: controller.signal })
      .then(data => { if (!controller.signal.aborted) setApplications(data); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load applications.'); });
    return () => controller.abort();
  }, [token, refresh]);
  function reload() { setError(''); setRefresh(value => value + 1); }
  async function submit(id: string, resubmit = false) {
    await apiRequest(`/applications/${encodeURIComponent(id)}/${resubmit ? 'resubmit' : 'submit'}`, { token: token ?? '', method: 'POST' });
    reload();
  }
  async function create() {
    setBusy(true); setError('');
    try { await apiRequest('/applications', { token: token ?? '', method: 'POST' }); reload(); }
    catch (e) { setError(e instanceof Error ? e.message : 'Unable to create draft.'); }
    finally { setBusy(false); }
  }
  const active = applications?.some(app => ['draft', 'submitted', 'resubmitted', 'needs_correction'].includes(app.status));
  return <main className="mx-auto max-w-4xl space-y-6 px-6 py-12">
    <h1 className="text-3xl font-bold">Your applications</h1>
    <p className="text-slate-300">Complete your company profile, upload documents, and verify extracted fields before submitting for human review.</p>
    <div className="flex gap-4"><Link className="secondary-button" to="/profile">Company profile</Link><Link className="secondary-button" to="/documents">Review documents</Link></div>
    {error && <p role="alert" className="text-rose-300">{error} <button onClick={reload}>Retry</button></p>}
    {!applications && !error && <p role="status">Loading applications…</p>}
    {applications && <>
      {!active && <button className="primary-button" disabled={busy} onClick={() => void create()}>{busy ? 'Creating…' : 'Create application draft'}</button>}
      {applications.length === 0 && <p>No applications yet.</p>}
      {applications.map(application => <div key={`${application.id}-${application.version}`} className="rounded-2xl border border-slate-700 bg-slate-900 p-6">
        <p className="mb-3 text-sm text-slate-400">{application.company_name} · {application.id}</p>
        <ApplicationStatus application={application} onSubmit={id => submit(id)} onResubmit={id => submit(id, true)} />
      </div>)}
    </>}
  </main>;
}
