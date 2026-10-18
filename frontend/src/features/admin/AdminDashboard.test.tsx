import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import type { Application, CaseDetail, ReviewApi } from '../applications/types';
import { AdminDashboard, ApplicationReview } from './AdminDashboard';
import { reviewApiForToken } from './reviewApi';
import { ApiError } from '../../shared/api';

const application: Application = { id: 'fictional-id', company_name: 'Sample Ltd', status: 'submitted', version: 3, submitted_at: null };
const detail: CaseDetail = {
  application, documents: [{ document_id: 'doc-1', document_type: 'trade_license', processing_status: 'processed' }],
  assessment: { score: 75, level: 'medium_review_priority', rules_version: 'v1', findings: [{
    code: 'expired_license', severity: 'error', description: 'License expired before reference date.',
    evidence: [{ document_id: 'doc-1', document_type: 'trade_license', field_name: 'expiry_date' }],
  }] },
  audit_events: [{ id: 'event-1', action: 'submitted', actor_user_id: 'vendor-1', created_at: '2026-10-18T00:00:00Z', note: '' }],
};
function api(): ReviewApi {
  return {
    dashboard: vi.fn().mockResolvedValue({ total: 1, awaiting_review: 1, approved: 0, rejected: 0, needs_correction: 0 }),
    queue: vi.fn().mockResolvedValue({ items: [application], total: 1, page: 1, page_size: 20 }),
    detail: vi.fn().mockResolvedValue(detail),
    review: vi.fn().mockResolvedValue({ ...detail, application: { ...application, status: 'approved' } }),
  };
}
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

test('loads counts and queue, sends filters, and opens actual case evidence', async () => {
  const client = api();
  render(<AdminDashboard api={client} />);
  expect(screen.getByRole('status')).toHaveTextContent('Loading reviews');
  fireEvent.click(await screen.findByRole('button', { name: 'Open Sample Ltd' }));
  expect(await screen.findByText(/Readiness: 75/)).toBeInTheDocument();
  expect(screen.getByText(/License expired before reference date/)).toBeInTheDocument();
  expect(screen.getByText(/vendor-1/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Status'), { target: { value: 'submitted' } });
  await waitFor(() => expect(client.queue).toHaveBeenLastCalledWith({ status: 'submitted', search: '', page: 1 }, expect.any(AbortSignal)));
});

test('shows empty results and forbidden errors without fabricated counts', async () => {
  const client = api();
  vi.mocked(client.queue).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
  const view = render(<AdminDashboard api={client} />);
  expect(await screen.findByText('No applications match these filters.')).toBeInTheDocument();
  view.unmount();
  vi.mocked(client.dashboard).mockRejectedValue(new ApiError(403, 'Administrator access required.'));
  render(<AdminDashboard api={client} />);
  expect(await screen.findByRole('alert')).toHaveTextContent('Administrator access required');
  expect(screen.queryByText('awaiting review')).not.toBeInTheDocument();
});

test('reject/correct require note and a decision carries the loaded version', async () => {
  const client = api();
  const onReviewed = vi.fn();
  render(<ApplicationReview id={application.id} api={client} onReviewed={onReviewed} />);
  const reject = await screen.findByRole('button', { name: 'Reject' });
  expect(reject).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Request corrections' })).toBeDisabled();
  fireEvent.change(screen.getByRole('textbox'), { target: { value: ' Please update license ' } });
  fireEvent.click(reject);
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  expect(client.review).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Confirm decision' }));
  await waitFor(() => expect(client.review).toHaveBeenCalledWith(application.id, 'rejected', 'Please update license', 3));
  await waitFor(() => expect(onReviewed).toHaveBeenCalledOnce());
  expect(screen.queryByRole('button', { name: 'Approve' })).not.toBeInTheDocument();
});

test('conflict disables stale decisions until case is reloaded', async () => {
  const client = api();
  vi.mocked(client.review).mockRejectedValue(new ApiError(409, 'This application changed. Reload it before reviewing.'));
  render(<ApplicationReview id={application.id} api={client} onReviewed={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: 'Approve' }));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm decision' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('This application changed');
  expect(screen.getByRole('button', { name: 'Approve' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Reload case' }));
  await waitFor(() => expect(screen.getByRole('button', { name: 'Approve' })).toBeEnabled());
});

test('review transport encodes ids and submits only decision, note, and version', async () => {
  const transport = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(detail)));
  await reviewApiForToken('fixture-token').review('a/b', 'approved', 'Reviewed', 3);
  expect(transport).toHaveBeenCalledWith(expect.stringContaining('/api/v1/admin/applications/a%2Fb/review'), expect.objectContaining({
    method: 'PATCH', body: JSON.stringify({ decision: 'approved', note: 'Reviewed', expected_version: 3 }),
  }));
  expect(new Headers(transport.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer fixture-token');
});
