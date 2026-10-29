import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap, unwrapEmpty } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { LOADING_MESSAGE } from '../../messages';
import { formatDateTime } from '../correspondence/format';

type Mailbox = components['schemas']['Mailbox'];

const POLL_INTERVAL_MS = 5000;
const DEFAULT_PORT = '993';
const MAILBOXES_KEY = ['mailboxes'];

function statusText(mailbox: Mailbox): string {
  switch (mailbox.status) {
    case 'pending':
      return 'Ожидает чтения';
    case 'reading':
      return 'Читается…';
    case 'read':
      return mailbox.last_read_at === null
        ? 'Прочитан'
        : `Прочитан ${formatDateTime(mailbox.last_read_at)}`;
    case 'failed':
      return `Ошибка: ${mailbox.error ?? ''}`;
  }
}

function MailboxRow({ mailbox }: { mailbox: Mailbox }): React.JSX.Element {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const refresh = useMutation({
    mutationFn: () =>
      unwrap(
        apiClient.POST('/api/v1/mailboxes/{mailbox_id}/refresh', {
          params: { path: { mailbox_id: mailbox.id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MAILBOXES_KEY }),
  });
  const disconnect = useMutation({
    mutationFn: () =>
      unwrapEmpty(
        apiClient.DELETE('/api/v1/mailboxes/{mailbox_id}', {
          params: { path: { mailbox_id: mailbox.id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: MAILBOXES_KEY }),
  });

  return (
    <tr>
      <td>{mailbox.login}</td>
      <td>{mailbox.server}</td>
      <td>{statusText(mailbox)}</td>
      <td>
        <ErrorAlert error={refresh.error ?? disconnect.error} />
        {confirming ? (
          <div className={styles.actions}>
            <span>{`Отключить ящик ${mailbox.login}? Прочитанные письма останутся.`}</span>
            <button
              type="button"
              className={styles.button}
              disabled={disconnect.isPending}
              onClick={() => {
                disconnect.mutate(undefined, {
                  onSettled: () => {
                    setConfirming(false);
                  },
                });
              }}
            >
              Отключить
            </button>
            <button
              type="button"
              className={styles.button}
              onClick={() => {
                setConfirming(false);
              }}
            >
              Отмена
            </button>
          </div>
        ) : (
          <div className={styles.actions}>
            <button
              type="button"
              className={styles.button}
              disabled={refresh.isPending}
              onClick={() => {
                refresh.mutate();
              }}
            >
              Обновить
            </button>
            <button
              type="button"
              className={styles.button}
              onClick={() => {
                setConfirming(true);
              }}
            >
              Отключить
            </button>
          </div>
        )}
      </td>
    </tr>
  );
}

function ConnectForm(): React.JSX.Element {
  const queryClient = useQueryClient();
  const [formKey, setFormKey] = useState(0);
  const connect = useMutation({
    mutationFn: (body: components['schemas']['MailboxConnect']) =>
      unwrap(apiClient.POST('/api/v1/mailboxes', { body })),
    onSuccess: async () => {
      setFormKey((key) => key + 1);
      await queryClient.invalidateQueries({ queryKey: MAILBOXES_KEY });
    },
  });
  const errors = fieldErrors(connect.error);

  return (
    <>
      <h2 className={styles.subheading}>Подключить ящик</h2>
      <form
        key={formKey}
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          connect.mutate({
            server: formValue(data, 'server'),
            port: Number(formValue(data, 'port')),
            login: formValue(data, 'login'),
            password: formValue(data, 'password'),
          });
        }}
      >
        <ErrorAlert error={errors.size > 0 ? null : connect.error} />
        <FormField name="server" label="Сервер IMAP" error={errors.get('server')} />
        <FormField
          name="port"
          label="Порт"
          defaultValue={DEFAULT_PORT}
          error={errors.get('port')}
        />
        <FormField name="login" label="Логин" autoComplete="username" error={errors.get('login')} />
        <FormField
          name="password"
          label="Пароль приложения"
          type="password"
          autoComplete="off"
          error={errors.get('password')}
        />
        <button type="submit" className={styles.button} disabled={connect.isPending}>
          Подключить
        </button>
      </form>
    </>
  );
}

// «Почтовые ящики»: the connected mailboxes, their reading status and the connect form.
export function MailboxesPage(): React.JSX.Element {
  const mailboxes = useQuery({
    queryKey: MAILBOXES_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/mailboxes')),
    refetchInterval: (query) =>
      query.state.data?.some((box) => box.status === 'pending' || box.status === 'reading') === true
        ? POLL_INTERVAL_MS
        : false,
  });

  return (
    <Panel title="Почтовые ящики" wide>
      <p>
        <Link to="/">На главную</Link>
      </p>
      <ErrorAlert error={mailboxes.error} />
      {mailboxes.isPending && <p>{LOADING_MESSAGE}</p>}
      {mailboxes.data?.length === 0 && <p>Ящики ещё не подключены</p>}
      {mailboxes.data !== undefined && mailboxes.data.length > 0 && (
        <table className={styles.table}>
          <tbody>
            {mailboxes.data.map((mailbox) => (
              <MailboxRow key={mailbox.id} mailbox={mailbox} />
            ))}
          </tbody>
        </table>
      )}
      <ConnectForm />
    </Panel>
  );
}
