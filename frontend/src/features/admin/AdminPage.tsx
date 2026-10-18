import { useMemo } from 'react';
import { useAuth } from '../auth/useAuth';
import { AdminDashboard } from './AdminDashboard';
import { reviewApiForToken } from './reviewApi';

export function AdminPage() {
  const { token, user } = useAuth();
  const api = useMemo(() => reviewApiForToken(token ?? ''), [token]);
  if (user?.role !== 'admin') return <main className="p-10"><h1>Administrator access required</h1></main>;
  return <AdminDashboard api={api} />;
}
