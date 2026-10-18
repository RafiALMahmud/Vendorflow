import { useState } from 'react';
import type { Application } from './types';

// Mount inside Dev 1's authenticated vendor page; callbacks call the real API.
export function ApplicationStatus({ application, onSubmit, onResubmit }: {
  application: Application;
  onSubmit: (id: string) => Promise<void>;
  onResubmit: (id: string) => Promise<void>;
}) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  async function send() {
    if (pending) return;
    setPending(true); setError('');
    try {
      await (application.status === 'draft' ? onSubmit : onResubmit)(application.id);
    } catch (e) { setError(e instanceof Error ? e.message : 'Unable to submit application.'); }
    finally { setPending(false); }
  }
  return <section aria-label="Application status" aria-busy={pending}>
    <h2>Application status: {application.status.replaceAll('_', ' ')}</h2>
    {application.correction_note && <p>Reviewer note: {application.correction_note}</p>}
    {error && <p role="alert">{error}</p>}
    {['draft', 'needs_correction'].includes(application.status) && <button className="primary-button mt-4" disabled={pending} onClick={() => void send()}>
      {pending ? 'Submitting…' : application.status === 'draft' ? 'Submit application' : 'Resubmit application'}
    </button>}
  </section>;
}
