import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { isNotSignedIn, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import styles from '../../components/ui.module.css';
import { LOADING_MESSAGE } from '../../messages';
import { useRefreshSession } from '../auth/AuthProvider';

type Member = components['schemas']['Member'];
type Role = Member['role'];
type MemberAction = { kind: 'deactivate' | 'reactivate' } | { kind: 'role'; role: Role };

const PAGE_SIZE = 100;
const ROLE_LABELS: Record<Role, string> = { administrator: 'Администратор', employee: 'Сотрудник' };

function applyAction(member: Member, action: MemberAction): Promise<Member> {
  const path = { member_id: member.id };
  switch (action.kind) {
    case 'deactivate':
      return unwrap(apiClient.POST('/api/v1/members/{member_id}/deactivate', { params: { path } }));
    case 'reactivate':
      return unwrap(apiClient.POST('/api/v1/members/{member_id}/reactivate', { params: { path } }));
    case 'role':
      return unwrap(
        apiClient.PUT('/api/v1/members/{member_id}/role', {
          params: { path },
          body: { role: action.role },
        }),
      );
  }
}

// The members of the organization, read page by page (cursor paging, 100 per page).
function useMembers() {
  return useInfiniteQuery({
    queryKey: ['members'],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      unwrap(
        apiClient.GET('/api/v1/members', {
          params: { query: { limit: PAGE_SIZE, cursor: pageParam } },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor,
    retry: false,
  });
}

// The members table with the actions on each member; the list is re-read after every action.
export function MembersSection(): React.JSX.Element {
  const queryClient = useQueryClient();
  const refreshSession = useRefreshSession();
  const members = useMembers();
  const change = useMutation({
    mutationFn: ({ member, action }: { member: Member; action: MemberAction }) =>
      applyAction(member, action),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['members'] }),
  });

  // A refused-as-signed-out request means the session ended (for example, the account was disabled).
  const isSignedOut = isNotSignedIn(members.error) || isNotSignedIn(change.error);
  useEffect(() => {
    if (isSignedOut) {
      refreshSession();
    }
  }, [isSignedOut, refreshSession]);

  const rows = members.data?.pages.flatMap((page) => page.items) ?? [];
  return (
    <section aria-labelledby="members-heading">
      <h2 id="members-heading" className={styles.subheading}>
        Члены организации
      </h2>
      {members.isPending && <p>{LOADING_MESSAGE}</p>}
      <ErrorAlert error={members.error} />
      <ErrorAlert error={change.error} />
      {members.isSuccess && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Имя</th>
              <th scope="col">Email</th>
              <th scope="col">Роль</th>
              <th scope="col">Состояние</th>
              <th scope="col">Действия</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((member) => (
              <tr key={member.id}>
                <td>{member.name}</td>
                <td>{member.email}</td>
                <td>{ROLE_LABELS[member.role]}</td>
                <td>{member.is_active ? 'Активен' : 'Отключён'}</td>
                <td>
                  <div className={styles.actions}>
                    <ActionButton
                      label={member.is_active ? 'Отключить' : 'Включить'}
                      disabled={change.isPending}
                      onPress={() => {
                        change.mutate({
                          member,
                          action: { kind: member.is_active ? 'deactivate' : 'reactivate' },
                        });
                      }}
                    />
                    <ActionButton
                      label={
                        member.role === 'administrator'
                          ? 'Сделать сотрудником'
                          : 'Сделать администратором'
                      }
                      disabled={change.isPending}
                      onPress={() => {
                        change.mutate({
                          member,
                          action: {
                            kind: 'role',
                            role: member.role === 'administrator' ? 'employee' : 'administrator',
                          },
                        });
                      }}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {members.hasNextPage && (
        <button
          type="button"
          className={styles.button}
          disabled={members.isFetchingNextPage}
          onClick={() => {
            void members.fetchNextPage();
          }}
        >
          Показать ещё
        </button>
      )}
    </section>
  );
}

function ActionButton(props: {
  label: string;
  disabled: boolean;
  onPress: () => void;
}): React.JSX.Element {
  return (
    <button
      type="button"
      className={styles.button}
      disabled={props.disabled}
      onClick={props.onPress}
    >
      {props.label}
    </button>
  );
}
