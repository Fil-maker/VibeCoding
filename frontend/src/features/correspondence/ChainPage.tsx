import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { ApiError, unwrap } from '../../api/request';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { NotFoundPage } from '../../components/NotFoundPage';
import { Panel } from '../../components/Panel';
import { ChainPlacement } from '../projects/ChainPlacement';
import { AttachmentButton } from './AttachmentButton';
import styles from './ChainPage.module.css';
import { formatAddress, formatAddresses, formatDateTime } from './format';

type EmailView = components['schemas']['EmailView'];

function EmailBlock({ email }: { email: EmailView }): React.JSX.Element {
  return (
    <article className={styles.email}>
      <p>
        <strong>Тема:</strong> {email.subject}
      </p>
      <p>
        <strong>От:</strong> {formatAddress(email.sender)}
      </p>
      <p>
        <strong>Кому:</strong> {formatAddresses(email.to)}
      </p>
      {email.cc.length > 0 && (
        <p>
          <strong>Копия:</strong> {formatAddresses(email.cc)}
        </p>
      )}
      <p>{formatDateTime(email.sent_at)}</p>
      <p className={styles.text}>{email.text}</p>
      {email.attachments.length > 0 && (
        <>
          <p>Вложения:</p>
          <ul className={styles.attachments}>
            {email.attachments.map((attachment) => (
              <AttachmentButton key={attachment.index} emailId={email.id} attachment={attachment} />
            ))}
          </ul>
        </>
      )}
    </article>
  );
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

// One reply chain: the subject, its «Проект» block, then its emails oldest first, each body as plain text.
export function ChainPage(): React.JSX.Element {
  const { id = '' } = useParams();
  const chain = useQuery({
    queryKey: ['reply-chains', id],
    queryFn: () =>
      unwrap(
        apiClient.GET('/api/v1/reply-chains/{chain_id}', { params: { path: { chain_id: id } } }),
      ),
    retry: (count, error) => !isNotFound(error) && count < 1,
  });

  if (isNotFound(chain.error)) {
    return <NotFoundPage />;
  }
  if (chain.data === undefined) {
    return (
      <Panel title="Переписка" wide>
        <LoadError error={chain.error} onRetry={() => void chain.refetch()} />
        {chain.error === null && <Loading />}
      </Panel>
    );
  }
  return (
    <Panel title={chain.data.subject} wide>
      <p>
        <Link to="/chains">К переписке</Link>
      </p>
      <ChainPlacement chainId={id} />
      {chain.data.emails.map((email) => (
        <EmailBlock key={email.id} email={email} />
      ))}
    </Panel>
  );
}
