import { useInfiniteQuery } from '@tanstack/react-query';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { emailCountLabel, formatAddresses, formatDate } from './format';

const EMPTY_CHAINS_MESSAGE = 'Писем пока нет: подключите почтовый ящик';

// «Переписка»: the reply chains, the chain with the latest email first, a page at a time.
export function ChainsPage(): React.JSX.Element {
  const chains = useInfiniteQuery({
    queryKey: ['reply-chains'],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      unwrap(
        apiClient.GET('/api/v1/reply-chains', {
          params: { query: pageParam === null ? {} : { cursor: pageParam } },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor,
  });

  const items = chains.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <Panel title="Переписка" wide>
      <p>
        <Link to="/">На главную</Link>
      </p>
      <LoadError error={chains.error} onRetry={() => void chains.refetch()} />
      {chains.isPending && <Loading />}
      {chains.data !== undefined && items.length === 0 && (
        <EmptyState
          message={EMPTY_CHAINS_MESSAGE}
          action={{ to: '/mailboxes', label: 'Подключить ящик' }}
        />
      )}
      {items.length > 0 && (
        <table className={styles.table}>
          <tbody>
            {items.map((chain) => (
              <tr key={chain.id}>
                <td>
                  <Link to={`/chains/${chain.id}`}>{chain.subject}</Link>
                </td>
                <td>{formatAddresses(chain.participants)}</td>
                <td>{emailCountLabel(chain.email_count)}</td>
                <td>{formatDate(chain.latest_email_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {chains.hasNextPage && (
        <button
          type="button"
          className={styles.button}
          disabled={chains.isFetchingNextPage}
          onClick={() => {
            void chains.fetchNextPage();
          }}
        >
          Показать ещё
        </button>
      )}
    </Panel>
  );
}
