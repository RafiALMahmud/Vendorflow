import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import { AuthProvider } from './AuthProvider';
import { useAuth } from './useAuth';
import { apiRequest, SESSION_EXPIRED_EVENT } from '../../shared/api';

function Probe() {
  const auth = useAuth();
  return <><p>{auth.user ? 'Signed in' : 'Signed out'}</p><p>{auth.sessionExpired ? 'Session expired' : ''}</p>
    <button onClick={() => void auth.login('fictional@example.com', 'fictional-password')}>Login</button>
    <button onClick={auth.logout}>Logout</button></>;
}
function mockLogin() {
  vi.spyOn(globalThis, 'fetch')
    .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'fixture', expires_in: 10 })))
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'u', email: 'fictional@example.com', role: 'vendor' })));
}
afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });

test('expires the in-memory user at the server token lifetime', async () => {
  vi.useFakeTimers();
  mockLogin(); render(<AuthProvider><Probe /></AuthProvider>);
  await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Login' })); });
  expect(screen.getByText('Signed in')).toBeInTheDocument();
  act(() => vi.advanceTimersByTime(10_000));
  expect(screen.getByText('Session expired')).toBeInTheDocument();
  expect(screen.getByText('Signed out')).toBeInTheDocument();
});

test('authenticated 401 emits session expiry while login failures do not', async () => {
  const listener = vi.fn();
  window.addEventListener(SESSION_EXPIRED_EVENT, listener);
  try {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response(JSON.stringify({ detail: 'Expired' }), { status: 401 }));
    await expect(apiRequest('/auth/me', { token: 'expired' })).rejects.toThrow('Expired');
    await expect(apiRequest('/auth/login', { method: 'POST', body: {} })).rejects.toThrow('Expired');
    expect(listener).toHaveBeenCalledOnce();
  } finally { window.removeEventListener(SESSION_EXPIRED_EVENT, listener); }
});

test('manual logout clears the user without an expiry warning', async () => {
  mockLogin(); render(<AuthProvider><Probe /></AuthProvider>);
  fireEvent.click(screen.getByRole('button', { name: 'Login' }));
  await screen.findByText('Signed in');
  fireEvent.click(screen.getByRole('button', { name: 'Logout' }));
  await waitFor(() => expect(screen.getByText('Signed out')).toBeInTheDocument());
  expect(screen.queryByText('Session expired')).not.toBeInTheDocument();
});
