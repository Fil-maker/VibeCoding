import { useQuery, useQueryClient } from '@tanstack/react-query';
import { createContext, useCallback, useContext, useMemo, type ReactNode } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { ApiError, unwrap } from '../../api/request';

export type Me = components['schemas']['Me'];

export type AuthState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'signedOut' }
  | { status: 'signedIn'; me: Me };

interface AuthContextValue {
  state: AuthState;
  // Records the user a sign-in, confirmation or acceptance returned; null after sign-out.
  setSession: (me: Me | null) => void;
}

const ME_KEY = ['auth', 'me'] as const;
const NOT_SIGNED_IN_STATUS = 401;

const AuthContext = createContext<AuthContextValue | null>(null);

// null means signed out: the API answers 401 for a missing, ended or expired session.
async function fetchMe(): Promise<Me | null> {
  try {
    return await unwrap(apiClient.GET('/api/v1/auth/me'));
  } catch (error) {
    if (error instanceof ApiError && error.status === NOT_SIGNED_IN_STATUS) {
      return null;
    }
    throw error;
  }
}

// The single place that knows who is signed in; guards and pages read it through useAuth.
export function AuthProvider({ children }: { children: ReactNode }): React.JSX.Element {
  const queryClient = useQueryClient();
  const meQuery = useQuery({ queryKey: ME_KEY, queryFn: fetchMe, retry: false });

  const setSession = useCallback(
    (me: Me | null): void => {
      queryClient.setQueryData(ME_KEY, me);
      if (me === null) {
        // Nothing of the previous user may stay in the cache.
        queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== 'auth' });
      }
    },
    [queryClient],
  );

  const state: AuthState = useMemo(() => {
    if (meQuery.isError) {
      return { status: 'error' };
    }
    if (meQuery.data === undefined) {
      return { status: 'loading' };
    }
    return meQuery.data === null
      ? { status: 'signedOut' }
      : { status: 'signedIn', me: meQuery.data };
  }, [meQuery.isError, meQuery.data]);

  const value = useMemo(() => ({ state, setSession }), [state, setSession]);
  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return value;
}

// Re-reads who is signed in, for a page whose request was refused as signed out.
export function useRefreshSession(): () => void {
  const queryClient = useQueryClient();
  return useCallback((): void => {
    void queryClient.invalidateQueries({ queryKey: ME_KEY });
  }, [queryClient]);
}
