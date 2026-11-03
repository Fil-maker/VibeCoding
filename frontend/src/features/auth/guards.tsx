import { Navigate, Outlet, useLocation, useSearchParams } from 'react-router';

import { Waiting } from '../../components/Waiting';
import { useAuth } from './AuthProvider';

// Only a path of this site may be a return address; "//host" would leave the site.
function safeNext(next: string | null): string {
  return next !== null && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

// Pages for signed-in users: a signed-out visitor goes to «Вход» and comes back after signing in.
export function RequireUser(): React.JSX.Element {
  const { state } = useAuth();
  const location = useLocation();
  if (state.status === 'loading' || state.status === 'error') {
    return <Waiting failed={state.status === 'error'} />;
  }
  if (state.status === 'signedOut') {
    const next = encodeURIComponent(`${location.pathname}${location.search}`);
    return <Navigate to={`/sign-in?next=${next}`} replace />;
  }
  return <Outlet />;
}

// Pages for signed-out visitors: a signed-in user goes on to the page they asked for, or the start page.
export function RequireGuest(): React.JSX.Element {
  const { state } = useAuth();
  const [params] = useSearchParams();
  if (state.status === 'loading' || state.status === 'error') {
    return <Waiting failed={state.status === 'error'} />;
  }
  if (state.status === 'signedIn') {
    return <Navigate to={safeNext(params.get('next'))} replace />;
  }
  return <Outlet />;
}
