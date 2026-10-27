import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import { fieldErrors, unwrapEmpty } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { PASSWORD_RESET_REQUESTED_MESSAGE } from '../../messages';

// «Восстановление пароля». The answer is the same for any email.
export function ForgotPasswordPage(): React.JSX.Element {
  const request = useMutation({
    mutationFn: (body: { email: string }) =>
      unwrapEmpty(apiClient.POST('/api/v1/auth/password-resets', { body })),
  });
  const errors = fieldErrors(request.error);

  return (
    <Panel title="Восстановление пароля">
      {request.isSuccess && <p role="status">{PASSWORD_RESET_REQUESTED_MESSAGE}</p>}
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          request.mutate({ email: formValue(new FormData(event.currentTarget), 'email') });
        }}
      >
        <ErrorAlert error={request.error} />
        <FormField
          name="email"
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.get('email')}
        />
        <button type="submit" className={styles.button} disabled={request.isPending}>
          Отправить ссылку
        </button>
      </form>
      <p className={styles.links}>
        <Link to="/sign-in">Вход</Link>
      </p>
    </Panel>
  );
}
