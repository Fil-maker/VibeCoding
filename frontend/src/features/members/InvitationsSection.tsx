import { useInfiniteQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, isNotSignedIn, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import styles from '../../components/ui.module.css';
import { INVITATION_MAIL_FAILED_MESSAGE, LOADING_MESSAGE } from '../../messages';
import { useRefreshSession } from '../auth/AuthProvider';

type Invitation = components['schemas']['Invitation'];
type InvitationStatus = Invitation['status'];

const PAGE_SIZE = 100;
const STATUS_LABELS: Record<InvitationStatus, string> = {
  sent: 'Отправлено',
  not_sent: 'Не отправлено',
  accepted: 'Принято',
  revoked: 'Отозвано',
  expired: 'Истекло',
};

const dateFormat = new Intl.DateTimeFormat('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });

// An invitation can be resent or revoked only while it is open.
function isOpen(invitation: Invitation): boolean {
  return invitation.status === 'sent' || invitation.status === 'not_sent';
}

// The invitations of the organization, read page by page (cursor paging, 100 per page).
function useInvitations() {
  return useInfiniteQuery({
    queryKey: ['invitations'],
    initialPageParam: null as string | null,
    queryFn: ({ pageParam }) =>
      unwrap(
        apiClient.GET('/api/v1/invitations', {
          params: { query: { limit: PAGE_SIZE, cursor: pageParam } },
        }),
      ),
    getNextPageParam: (page) => page.next_cursor,
    retry: false,
  });
}

// The invite form and the invitations list, newest first, with resend and revoke for open ones.
export function InvitationsSection(): React.JSX.Element {
  const queryClient = useQueryClient();
  const refreshSession = useRefreshSession();
  const invitations = useInvitations();
  const refresh = (): Promise<void> => queryClient.invalidateQueries({ queryKey: ['invitations'] });

  const invite = useMutation({
    mutationFn: (email: string) =>
      unwrap(apiClient.POST('/api/v1/invitations', { body: { email } })),
    onSettled: refresh,
  });
  const resend = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        apiClient.POST('/api/v1/invitations/{invitation_id}/resend', {
          params: { path: { invitation_id: id } },
        }),
      ),
    onSettled: refresh,
  });
  const revoke = useMutation({
    mutationFn: (id: string) =>
      unwrap(
        apiClient.POST('/api/v1/invitations/{invitation_id}/revoke', {
          params: { path: { invitation_id: id } },
        }),
      ),
    onSettled: refresh,
  });

  const isSignedOut = [invitations.error, invite.error, resend.error, revoke.error].some(
    isNotSignedIn,
  );
  useEffect(() => {
    if (isSignedOut) {
      refreshSession();
    }
  }, [isSignedOut, refreshSession]);

  const isMailFailed = invite.data?.status === 'not_sent' || resend.data?.status === 'not_sent';
  const isBusy = resend.isPending || revoke.isPending;
  const rows = invitations.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <section aria-labelledby="invitations-heading">
      <h2 id="invitations-heading" className={styles.subheading}>
        Приглашения
      </h2>
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          invite.mutate(formValue(new FormData(event.currentTarget), 'email'));
        }}
      >
        <ErrorAlert error={invite.error} />
        <FormField
          name="email"
          label="Email"
          type="email"
          error={fieldErrors(invite.error).get('email')}
        />
        <button type="submit" className={styles.button} disabled={invite.isPending}>
          Пригласить
        </button>
      </form>
      {isMailFailed && (
        <p role="alert" className={styles.error}>
          {INVITATION_MAIL_FAILED_MESSAGE}
        </p>
      )}
      {invitations.isPending && <p>{LOADING_MESSAGE}</p>}
      <ErrorAlert error={invitations.error} />
      <ErrorAlert error={resend.error} />
      <ErrorAlert error={revoke.error} />
      {invitations.isSuccess && (
        <table className={styles.table}>
          <thead>
            <tr>
              <th scope="col">Email</th>
              <th scope="col">Дата отправки</th>
              <th scope="col">Статус</th>
              <th scope="col">Действия</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((invitation) => (
              <tr key={invitation.id}>
                <td>{invitation.email}</td>
                <td>
                  {invitation.sent_at === null
                    ? '—'
                    : dateFormat.format(new Date(invitation.sent_at))}
                </td>
                <td>{STATUS_LABELS[invitation.status]}</td>
                <td>
                  {isOpen(invitation) && (
                    <div className={styles.actions}>
                      <button
                        type="button"
                        className={styles.button}
                        disabled={isBusy}
                        onClick={() => {
                          resend.mutate(invitation.id);
                        }}
                      >
                        Отправить ещё раз
                      </button>
                      <button
                        type="button"
                        className={styles.button}
                        disabled={isBusy}
                        onClick={() => {
                          revoke.mutate(invitation.id);
                        }}
                      >
                        Отозвать
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {invitations.hasNextPage && (
        <button
          type="button"
          className={styles.button}
          disabled={invitations.isFetchingNextPage}
          onClick={() => {
            void invitations.fetchNextPage();
          }}
        >
          Показать ещё
        </button>
      )}
    </section>
  );
}
