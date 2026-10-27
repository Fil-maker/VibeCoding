import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrapEmpty } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { isAdministrator, useAuth } from '../auth/AuthProvider';

// The start page: who is signed in, their organization, the members link for an administrator, sign-out.
export function StartPage(): React.JSX.Element | null {
  const { state, setSession } = useAuth();
  const signOut = useMutation({
    mutationFn: () => unwrapEmpty(apiClient.DELETE('/api/v1/auth/sessions/current')),
    onSuccess: () => {
      setSession(null);
    },
  });

  if (state.status !== 'signedIn') {
    return null;
  }
  const { me } = state;
  return (
    <Panel title="VibeCoding">
      <p>{me.name}</p>
      <p className={styles.muted}>{me.organization.name}</p>
      {isAdministrator(me) && (
        <p>
          <Link to="/members">Участники</Link>
        </p>
      )}
      <ErrorAlert error={signOut.error} />
      <button
        type="button"
        className={styles.button}
        disabled={signOut.isPending}
        onClick={() => {
          signOut.mutate();
        }}
      >
        Выйти
      </button>
    </Panel>
  );
}
