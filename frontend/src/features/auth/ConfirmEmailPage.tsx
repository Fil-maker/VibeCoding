import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { Navigate, useLocation } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { INVALID_LINK_MESSAGE, LOADING_MESSAGE } from '../../messages';
import { readFragmentToken } from '../../urlToken';
import { useAuth } from './AuthProvider';

// «Подтверждение email». The link is single-use, so the token is sent exactly once on arrival.
export function ConfirmEmailPage(): React.JSX.Element {
  const token = readFragmentToken(useLocation().hash);
  const { state, setSession } = useAuth();
  const confirm = useMutation({
    mutationFn: (value: string) =>
      unwrap(apiClient.POST('/api/v1/auth/email-confirmations', { body: { token: value } })),
    onSuccess: setSession,
  });
  const { mutate } = confirm;
  const hasStarted = useRef(false);

  useEffect(() => {
    if (token !== null && !hasStarted.current) {
      hasStarted.current = true;
      mutate(token);
    }
  }, [token, mutate]);

  // Wait for the session to be recorded: leaving earlier would bounce through «Вход».
  if (confirm.isSuccess && state.status === 'signedIn') {
    return <Navigate to="/" replace />;
  }
  return (
    <Panel title="Подтверждение email">
      {token === null && (
        <p role="alert" className={styles.error}>
          {INVALID_LINK_MESSAGE}
        </p>
      )}
      {token !== null && !confirm.isError && <p>{LOADING_MESSAGE}</p>}
      <ErrorAlert error={confirm.error} />
    </Panel>
  );
}
