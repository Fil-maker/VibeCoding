import { useAuth } from '../auth/AuthProvider';
import { Waiting } from '../../components/Waiting';
import { AppLayout } from './AppLayout';
import { GuestLayout } from './GuestLayout';

// For pages open to everyone: the signed-in frame for a signed-in user, the guest frame otherwise.
export function AuthFrame(): React.JSX.Element {
  const { state } = useAuth();
  if (state.status === 'loading' || state.status === 'error') {
    return <Waiting failed={state.status === 'error'} />;
  }
  return state.status === 'signedIn' ? <AppLayout /> : <GuestLayout />;
}
