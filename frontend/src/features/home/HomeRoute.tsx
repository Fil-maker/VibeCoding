import { useAuth } from '../auth/AuthProvider';
import { LandingPage } from './LandingPage';
import { StartPage } from './StartPage';

// «/»: the landing page for a guest, the start page for a signed-in user (AuthFrame chooses the frame).
export function HomeRoute(): React.JSX.Element {
  const { state } = useAuth();
  return state.status === 'signedIn' ? <StartPage /> : <LandingPage />;
}
