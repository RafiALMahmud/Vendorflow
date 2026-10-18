import type { ReviewApi } from '../applications/types';
import { apiRequest } from '../../shared/api';

export function reviewApiForToken(token: string): ReviewApi {
  return {
    dashboard: signal => apiRequest('/admin/dashboard', { token, signal }),
    queue: (query, signal) => apiRequest(`/admin/applications?${new URLSearchParams({
      status: query.status, search: query.search, page: String(query.page), page_size: '20',
    })}`, { token, signal }),
    detail: (id, signal) => apiRequest(`/admin/applications/${encodeURIComponent(id)}`, { token, signal }),
    review: (id, decision, note, expectedVersion) => apiRequest(`/admin/applications/${encodeURIComponent(id)}/review`, {
      token, method: 'PATCH', body: { decision, note, expected_version: expectedVersion },
    }),
  };
}
