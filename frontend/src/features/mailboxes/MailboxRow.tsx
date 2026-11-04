import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { unwrap, unwrapEmpty } from '../../api/request';
import { Button } from '../../components/Button';
import { ErrorAlert } from '../../components/ErrorAlert';
import styles from '../../components/ui.module.css';
import { formatDateTime } from '../correspondence/format';
import { MAILBOXES_KEY } from './mailboxesKey';
import { serviceForServer } from './mailServices';
import { ServiceSteps } from './ServiceSteps';

type Mailbox = components['schemas']['Mailbox'];

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

// One row of the mailbox list. «Как исправить» appears only for a refused sign-in on a server of a
// known service with steps: the demo and unknown servers have none to show.
export function MailboxRow({ mailbox }: { mailbox: Mailbox }): React.JSX.Element {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const [showingSteps, setShowingSteps] = useState(false);
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
  const service = mailbox.error_code === 'sign_in_failed' ? serviceForServer(mailbox.server) : null;
  const hasSteps = service !== null && service.howToTitle !== null;

  return (
    <tr>
      <td>{mailbox.login}</td>
      <td>{mailbox.server}</td>
      <td>
        {statusText(mailbox)}
        {hasSteps && showingSteps && <ServiceSteps service={service} />}
      </td>
      <td>
        <ErrorAlert error={refresh.error ?? disconnect.error} />
        {confirming ? (
          <div className={styles.actions}>
            <span>{`Отключить ящик ${mailbox.login}? Прочитанные письма останутся.`}</span>
            <Button
              kind="danger"
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
            </Button>
            <Button
              onClick={() => {
                setConfirming(false);
              }}
            >
              Отмена
            </Button>
          </div>
        ) : (
          <div className={styles.actions}>
            {hasSteps && (
              <Button
                aria-expanded={showingSteps}
                onClick={() => {
                  setShowingSteps(true);
                }}
              >
                Как исправить
              </Button>
            )}
            <Button
              disabled={refresh.isPending}
              onClick={() => {
                refresh.mutate();
              }}
            >
              Обновить
            </Button>
            <Button
              onClick={() => {
                setConfirming(true);
              }}
            >
              Отключить
            </Button>
          </div>
        )}
      </td>
    </tr>
  );
}
