import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import { fieldErrors, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { useAuth } from './AuthProvider';

// «Вход». After a success the signed-in user lands where RequireGuest sends them (the `next` address).
export function SignInPage(): React.JSX.Element {
  const { setSession } = useAuth();
  const signIn = useMutation({
    mutationFn: (body: { email: string; password: string }) =>
      unwrap(apiClient.POST('/api/v1/auth/sessions', { body })),
    onSuccess: setSession,
  });

  const errors = fieldErrors(signIn.error);

  return (
    <Panel title="Вход">
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          signIn.mutate({ email: formValue(data, 'email'), password: formValue(data, 'password') });
        }}
      >
        <ErrorAlert error={signIn.error} />
        <FormField
          name="email"
          label="Email"
          type="email"
          autoComplete="username"
          error={errors.get('email')}
        />
        <FormField
          name="password"
          label="Пароль"
          type="password"
          autoComplete="current-password"
          error={errors.get('password')}
        />
        <button type="submit" className={styles.button} disabled={signIn.isPending}>
          Войти
        </button>
      </form>
      <p className={styles.links}>
        <Link to="/forgot-password">Забыли пароль?</Link>
        <Link to="/register">Регистрация</Link>
      </p>
    </Panel>
  );
}
