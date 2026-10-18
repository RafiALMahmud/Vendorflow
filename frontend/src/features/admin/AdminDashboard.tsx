import { useEffect, useState } from 'react';
import type { CaseDetail, Dashboard, QueuePage, QueueQuery, ReviewApi, ReviewDecision } from '../applications/types';
import './review.css';
import { DecisionDialog } from './DecisionDialog';

type Props = { api: ReviewApi };
type Data = { dashboard: Dashboard; queue: QueuePage };

export function AdminDashboard({ api }: Props) {
  const [query, setQuery] = useState<QueueQuery>({ status: '', search: '', page: 1 });
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState('');
  const [refresh, setRefresh] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api.dashboard(controller.signal), api.queue(query, controller.signal)])
      .then(([dashboard, queue]) => { if (!controller.signal.aborted) setData({ dashboard, queue }); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load reviews.'); });
    return () => controller.abort();
  }, [api, query, refresh]);
  function reload() { setData(null); setError(''); setRefresh(value => value + 1); }
  function filter(next: Partial<QueueQuery>) { setData(null); setError(''); setQuery({ ...query, ...next }); }
  return <main className="review-workspace mx-auto max-w-6xl space-y-6 p-6 text-slate-100">
    <h1 className="text-3xl font-bold">Application reviews</h1>
    <p>Document completeness and consistency assist human review. Scores are not fraud probabilities.</p>
    <div className="flex flex-wrap gap-4">
      <label>Status <select value={query.status} onChange={e => filter({ status: e.target.value, page: 1 })}>
        <option value="">All statuses</option>
        {['draft', 'submitted', 'resubmitted', 'needs_correction', 'approved', 'rejected'].map(s => <option key={s} value={s}>{s.replaceAll('_', ' ')}</option>)}
      </select></label>
      <label>Search companies <input value={query.search} onChange={e => filter({ search: e.target.value, page: 1 })} /></label>
      <button onClick={reload}>Refresh reviews</button>
    </div>
    {error ? <p role="alert">{error} <button onClick={reload}>Retry</button></p> : !data ? <p role="status">Loading reviews…</p> : <>
      <dl className="grid grid-cols-2 gap-4 md:grid-cols-5">{Object.entries(data.dashboard).map(([label, count]) =>
        <div className="rounded border p-4" key={label}><dt>{label.replaceAll('_', ' ')}</dt><dd className="text-2xl font-bold">{count}</dd></div>)}</dl>
      {data.queue.items.length === 0 ? <p>No applications match these filters.</p> : <div className="overflow-x-auto"><table className="w-full text-left">
        <caption className="sr-only">Vendor application review queue</caption>
        <thead><tr><th scope="col">Company</th><th scope="col">Status</th><th scope="col">Submitted</th><th scope="col">Review</th></tr></thead>
        <tbody>{data.queue.items.map(item => <tr key={item.id} data-application-id={item.id}><td>{item.company_name}</td><td>{item.status.replaceAll('_', ' ')}</td>
          <td>{item.submitted_at ? new Date(item.submitted_at).toLocaleString() : 'Not submitted'}</td>
          <td><button onClick={() => setSelected(item.id)}>Open {item.company_name}</button></td></tr>)}</tbody>
      </table></div>}
      <nav aria-label="Queue pages" className="flex gap-4">
        <button disabled={query.page <= 1} onClick={() => filter({ page: query.page - 1 })}>Previous</button>
        <span>Page {data.queue.page} · {data.queue.total} applications</span>
        <button disabled={data.queue.page * data.queue.page_size >= data.queue.total} onClick={() => filter({ page: query.page + 1 })}>Next</button>
      </nav>
    </>}
    {selected && <section className="border-t pt-6"><button onClick={() => setSelected(null)}>Close case</button>
      <ApplicationReview key={selected} id={selected} api={api} onReviewed={reload} /></section>}
  </main>;
}

export function ApplicationReview({ id, api, onReviewed }: Props & { id: string; onReviewed: () => void }) {
  const [detail, setDetail] = useState<CaseDetail | null>(null);
  const [error, setError] = useState('');
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [stale, setStale] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [decision, setDecision] = useState<ReviewDecision | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    api.detail(id, controller.signal).then(data => { if (!controller.signal.aborted) setDetail(data); })
      .catch((e: unknown) => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load case.'); });
    return () => controller.abort();
  }, [api, id, refresh]);
  async function decide(decision: ReviewDecision) {
    if (!detail || busy || stale) return;
    setBusy(true); setError('');
    try {
      setDetail(await api.review(id, decision, note.trim(), detail.application.version));
      setNote(''); onReviewed();
    } catch (e) { setError(e instanceof Error ? e.message : 'Review failed.'); setStale(true); }
    finally { setBusy(false); setDecision(null); }
  }
  async function download(documentId: string, documentType: string) {
    if (!api.downloadEvidence) return;
    setDownloading(documentId); setError('');
    try {
      const blob = await api.downloadEvidence(id, documentId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url; link.download = `${documentType}.${blob.type.includes('pdf') ? 'pdf' : blob.type.includes('png') ? 'png' : 'jpg'}`;
      link.click(); URL.revokeObjectURL(url);
    } catch (error) { setError(error instanceof Error ? error.message : 'Unable to download evidence.'); }
    finally { setDownloading(null); }
  }
  return <article className="space-y-4" aria-busy={busy}>
    {error && <p role="alert">{error}</p>}
    <button disabled={busy} onClick={() => { setDetail(null); setError(''); setStale(false); setRefresh(v => v + 1); }}>Reload case</button>
    {!detail ? <p role="status">Loading case…</p> : <>
      <h2 className="text-2xl font-bold">{detail.application.company_name}</h2>
      <p>Status: {detail.application.status.replaceAll('_', ' ')}</p>
      <h3 className="font-bold">Review findings</h3>
      {detail.assessment ? <><p>Readiness: {detail.assessment.score}/100 · {detail.assessment.level.replaceAll('_', ' ')} · {detail.assessment.rules_version}</p>
        {detail.assessment.findings.length === 0 && <p>No rule findings. A human decision is still required.</p>}
        <ul>{detail.assessment.findings.map(f => <li key={`${f.code}-${JSON.stringify(f.evidence)}`}><strong>{f.severity}: {f.code}</strong> — {f.description}
          <ul>{f.evidence.map((e, i) => <li key={i}>{e.document_type} · {e.document_id ?? 'Missing document'} · {e.field_name ?? 'Document'}</li>)}</ul></li>)}</ul></> : <p>No assessment yet.</p>}
      <h3 className="font-bold">Document evidence</h3>
      <ul>{detail.documents.map(d => <li key={d.document_id}>{d.document_type} · {d.document_id} · {d.processing_status}
        {api.downloadEvidence && <button className="ml-3" disabled={downloading !== null} onClick={() => void download(d.document_id, d.document_type)}>
          {downloading === d.document_id ? 'Downloading…' : `Download ${d.document_type.replaceAll('_', ' ')}`}</button>}
        <dl>{Object.entries(d.fields ?? {}).map(([name, field]) => <div key={name} className="my-2 rounded border border-slate-700 p-3">
          <dt className="font-semibold">{name.replaceAll('_', ' ')}</dt>
          <dd>Extracted: {field.raw_value ?? 'Unreadable'} · Reviewed: {field.confirmed_value ?? 'Unverified'} · {field.review_status}</dd>
        </div>)}</dl>
      </li>)}</ul>
      {['submitted', 'resubmitted'].includes(detail.application.status) && <fieldset disabled={busy || stale} className="space-y-3">
        <legend>Human review decision</legend>
        <label>Review note (required for rejection or correction)<textarea maxLength={4000} value={note} onChange={e => setNote(e.target.value)} className="block w-full border p-2" /></label>
        <div className="flex flex-wrap gap-4"><button onClick={() => setDecision('approved')}>Approve</button>
          <button disabled={!note.trim()} onClick={() => setDecision('rejected')}>Reject</button>
          <button disabled={!note.trim()} onClick={() => setDecision('needs_correction')}>Request corrections</button></div>
      </fieldset>}
      {decision && <DecisionDialog decision={decision} note={note} busy={busy}
        onCancel={() => setDecision(null)} onConfirm={() => void decide(decision)} />}
      <h3 className="font-bold">Audit history</h3>
      {detail.audit_events.length === 0 ? <p>No recorded events.</p> : <ol>{detail.audit_events.map(e =>
        <li key={e.id}><time dateTime={e.created_at}>{new Date(e.created_at).toLocaleString()}</time> · {e.actor_user_id} · {e.action} · {e.note}</li>)}</ol>}
    </>}
  </article>;
}
