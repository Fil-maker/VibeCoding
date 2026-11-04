import { useQuery } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { ConnectForm } from './ConnectForm';
import { MailboxRow } from './MailboxRow';
import { MAILBOXES_KEY } from './mailboxesKey';

const POLL_INTERVAL_MS = 5000;
const READ_ONLY_EXPLANATION =
  'Приложение только читает письма: не отправляет, не удаляет и не помечает их прочитанными. Для входа нужен пароль приложения — отдельный пароль для почтовых программ, который можно отозвать, не меняя основной.';

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
      <LoadError error={mailboxes.error} onRetry={() => void mailboxes.refetch()} />
      {mailboxes.isPending && <Loading />}
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
      <p>{READ_ONLY_EXPLANATION}</p>
      <ConnectForm />
    </Panel>
  );
}
