import { useMutation, useQuery } from '@tanstack/react-query';
import { Navigate, useLocation } from 'react-router';

import { apiClient } from '../../api/client';
import { fieldErrors, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { INVALID_INVITATION_MESSAGE, LOADING_MESSAGE } from '../../messages';
import { readFragmentToken } from '../../urlToken';
import { useAuth } from '../auth/AuthProvider';

// «Приглашение»: shows the organization and the invited email, then joins with a name and a password.
export function InvitationPage(): React.JSX.Element {
  const token = readFragmentToken(useLocation().hash);
  const { state, setSession } = useAuth();
  const preview = useQuery({
    queryKey: ['invitation-preview', token],
    queryFn: () =>
      unwrap(apiClient.POST('/api/v1/invitations/preview', { body: { token: token ?? '' } })),
    enabled: token !== null,
    retry: false,
  });
  const accept = useMutation({
    mutationFn: (body: { token: string; name: string; password: string }) =>
      unwrap(apiClient.POST('/api/v1/invitations/accept', { body })),
    onSuccess: setSession,
  });
  const errors = fieldErrors(accept.error);

  // Wait for the session to be recorded: leaving earlier would bounce through «Вход».
  if (accept.isSuccess && state.status === 'signedIn') {
    return <Navigate to="/" replace />;
  }
  if (token === null) {
    return (
      <Panel title="Приглашение">
        <p role="alert" className={styles.error}>
          {INVALID_INVITATION_MESSAGE}
        </p>
      </Panel>
    );
  }
  return (
    <Panel title="Приглашение">
      {preview.isPending && <p>{LOADING_MESSAGE}</p>}
      <ErrorAlert error={preview.error} />
      {preview.isSuccess && (
        <>
          <p>
            Организация: <strong>{preview.data.organization_name}</strong>
          </p>
          <p>
            Email: <strong>{preview.data.email}</strong>
          </p>
          <form
            className={styles.form}
            noValidate
            onSubmit={(event) => {
              event.preventDefault();
              const data = new FormData(event.currentTarget);
              accept.mutate({
                token,
                name: formValue(data, 'name'),
                password: formValue(data, 'password'),
              });
            }}
          >
            <ErrorAlert error={accept.error} />
            <FormField name="name" label="Имя" autoComplete="name" error={errors.get('name')} />
            <FormField
              name="password"
              label="Пароль"
              type="password"
              autoComplete="new-password"
              error={errors.get('password')}
            />
            <button type="submit" className={styles.button} disabled={accept.isPending}>
              Принять приглашение
            </button>
          </form>
        </>
      )}
    </Panel>
  );
}
