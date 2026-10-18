import type { CaseDetail, Dashboard, QueuePage, ReviewApi } from '../applications/types';

export class ReviewApiError extends Error {
  constructor(public status: number) {
    super(status === 403 ? 'Administrator access required.' : status === 401
      ? 'Please sign in again.' : status === 409
      ? 'This application changed. Reload it before reviewing.' : 'The request failed. Please retry.');
  }
}

// Supply Dev 1's authenticated transport after it merges. No alternate token store.
export function createReviewApi(authenticatedFetch: typeof fetch, baseUrl: string): ReviewApi {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await authenticatedFetch(`${baseUrl}${path}`, init);
    if (!response.ok) throw new ReviewApiError(response.status);
    return response.json() as Promise<T>;
  }
  return {
    dashboard: signal => request<Dashboard>('/admin/dashboard', { signal }),
    queue: (query, signal) => request<QueuePage>(`/admin/applications?${new URLSearchParams({
      status: query.status, search: query.search, page: String(query.page), page_size: '20',
    })}`, { signal }),
    detail: (id, signal) => request<CaseDetail>(`/admin/applications/${encodeURIComponent(id)}`, { signal }),
    review: (id, decision, note, expectedVersion) => request<CaseDetail>(
      `/admin/applications/${encodeURIComponent(id)}/review`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note, expected_version: expectedVersion }),
      }),
  };
}
