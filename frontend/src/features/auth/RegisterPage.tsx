import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import { fieldErrors, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { confirmationSentMessage, REGISTRATION_MAIL_FAILED_MESSAGE } from '../../messages';

// «Регистрация». The confirmation link in the email signs the registrant in.
export function RegisterPage(): React.JSX.Element {
  const register = useMutation({
    mutationFn: (body: {
      organization_name: string;
      name: string;
      email: string;
      password: string;
    }) => unwrap(apiClient.POST('/api/v1/auth/registrations', { body })),
  });
  const errors = fieldErrors(register.error);

  return (
    <Panel title="Регистрация">
      {register.isSuccess && (
        <p role={register.data.email_sent ? 'status' : 'alert'}>
          {register.data.email_sent
            ? confirmationSentMessage(register.data.email)
            : REGISTRATION_MAIL_FAILED_MESSAGE}
        </p>
      )}
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          register.mutate({
            organization_name: formValue(data, 'organization_name'),
            name: formValue(data, 'name'),
            email: formValue(data, 'email'),
            password: formValue(data, 'password'),
          });
        }}
      >
        <ErrorAlert error={register.error} />
        <FormField
          name="organization_name"
          label="Название организации"
          error={errors.get('organization_name')}
        />
        <FormField name="name" label="Имя" autoComplete="name" error={errors.get('name')} />
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
          autoComplete="new-password"
          error={errors.get('password')}
        />
        <button type="submit" className={styles.button} disabled={register.isPending}>
          Зарегистрироваться
        </button>
      </form>
      <p className={styles.links}>
        <Link to="/sign-in">Вход</Link>
      </p>
    </Panel>
  );
}
