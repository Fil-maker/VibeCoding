import { useMutation } from '@tanstack/react-query';
import { Link, useLocation } from 'react-router';

import { apiClient } from '../../api/client';
import { fieldErrors, unwrapEmpty } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { INVALID_LINK_MESSAGE, PASSWORD_CHANGED_MESSAGE } from '../../messages';
import { readFragmentToken } from '../../urlToken';

// «Новый пароль». The token is in the link's fragment.
export function ResetPasswordPage(): React.JSX.Element {
  const token = readFragmentToken(useLocation().hash);
  const reset = useMutation({
    mutationFn: (body: { token: string; password: string }) =>
      unwrapEmpty(apiClient.POST('/api/v1/auth/password-resets/complete', { body })),
  });
  const errors = fieldErrors(reset.error);

  if (token === null) {
    return (
      <Panel title="Новый пароль">
        <p role="alert" className={styles.error}>
          {INVALID_LINK_MESSAGE}
        </p>
      </Panel>
    );
  }

  return (
    <Panel title="Новый пароль">
      {reset.isSuccess ? (
        <>
          <p role="status">{PASSWORD_CHANGED_MESSAGE}</p>
          <p className={styles.links}>
            <Link to="/sign-in">Вход</Link>
          </p>
        </>
      ) : (
        <form
          className={styles.form}
          noValidate
          onSubmit={(event) => {
            event.preventDefault();
            const password = formValue(new FormData(event.currentTarget), 'password');
            reset.mutate({ token, password });
          }}
        >
          <ErrorAlert error={reset.error} />
          <FormField
            name="password"
            label="Новый пароль"
            type="password"
            autoComplete="new-password"
            error={errors.get('password')}
          />
          <button type="submit" className={styles.button} disabled={reset.isPending}>
            Сохранить пароль
          </button>
        </form>
      )}
    </Panel>
  );
}
