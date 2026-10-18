import { useEffect, useId, useRef } from 'react';
import type { ReviewDecision } from '../applications/types';

export function DecisionDialog({ decision, note, busy, onCancel, onConfirm }: {
  decision: ReviewDecision; note: string; busy: boolean;
  onCancel: () => void; onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }, []);
  return <dialog ref={ref} aria-labelledby={titleId} onCancel={event => {
    event.preventDefault(); if (!busy) onCancel();
  }} className="space-y-4 rounded-2xl border border-slate-600 bg-slate-900 p-6 text-slate-100 shadow-2xl">
    <h2 id={titleId} className="text-xl font-bold">Confirm {decision.replaceAll('_', ' ')}</h2>
    <p>This human decision and your note will be saved in the application audit history.</p>
    <p>Note: {note.trim() || 'No note supplied.'}</p>
    <div className="flex gap-3"><button disabled={busy} onClick={onCancel}>Cancel</button>
      <button disabled={busy} onClick={onConfirm}>{busy ? 'Saving decision…' : 'Confirm decision'}</button></div>
  </dialog>;
}
