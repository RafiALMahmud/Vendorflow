import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { ApplicationStatus } from './ApplicationStatus';
import type { Application } from './types';

const draft: Application = { id: 'fictional-id', company_name: 'Sample Ltd', status: 'draft', version: 0, submitted_at: null };
afterEach(cleanup);

test('draft submits through its callback with pending protection', async () => {
  let finish!: () => void;
  const submit = vi.fn().mockImplementation(() => new Promise<void>(resolve => { finish = resolve; }));
  render(<ApplicationStatus application={draft} onSubmit={submit} onResubmit={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Submit application' }));
  expect(screen.getByRole('button', { name: 'Submitting…' })).toBeDisabled();
  expect(submit).toHaveBeenCalledExactlyOnceWith(draft.id);
  finish();
  await waitFor(() => expect(screen.getByRole('button', { name: 'Submit application' })).toBeEnabled());
});

test('correction shows reason, resubmits, and reports errors', async () => {
  const resubmit = vi.fn().mockRejectedValue(new Error('Please sign in again.'));
  render(<ApplicationStatus application={{ ...draft, status: 'needs_correction', correction_note: 'Update license' }} onSubmit={vi.fn()} onResubmit={resubmit} />);
  expect(screen.getByText('Reviewer note: Update license')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Resubmit application' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Please sign in again');
  expect(resubmit).toHaveBeenCalledExactlyOnceWith(draft.id);
});

test('approved application has no submission action', () => {
  render(<ApplicationStatus application={{ ...draft, status: 'approved' }} onSubmit={vi.fn()} onResubmit={vi.fn()} />);
  expect(screen.queryByRole('button')).not.toBeInTheDocument();
});
