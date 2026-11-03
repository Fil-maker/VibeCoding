import { useMutation } from '@tanstack/react-query';
import { useState, type KeyboardEvent } from 'react';
import { flushSync } from 'react-dom';
import { Link, NavLink, useLocation, useNavigate } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrapEmpty } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { useAuth } from '../auth/AuthProvider';
import styles from './AppShell.module.css';

const MENU_ID = 'header-menu';
const SECTIONS = [
  { to: '/projects', label: 'Проекты' },
  { to: '/chains', label: 'Переписка' },
  { to: '/mailboxes', label: 'Почтовые ящики' },
  { to: '/rules', label: 'Правила' },
] as const;

// The header of a signed-in user: the sections, the name, «Выйти», and «Меню» that folds them when narrow.
export function AppHeader(): React.JSX.Element {
  const { state, setSession } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  // The menu is open for the path it was opened on, so a route change closes it without an effect.
  const [openAt, setOpenAt] = useState<string | null>(null);
  const isOpen = openAt === pathname;
  const signOut = useMutation({
    mutationFn: () => unwrapEmpty(apiClient.DELETE('/api/v1/auth/sessions/current')),
    onSuccess: () => {
      // Commit the move to «/» before the session clears: a guard on the old page must never see «signed out».
      flushSync(() => {
        void navigate('/');
      });
      setSession(null);
    },
  });

  const closeOnEscape = (event: KeyboardEvent<HTMLElement>): void => {
    if (event.key === 'Escape') {
      setOpenAt(null);
    }
  };

  return (
    <header className={styles.header} onKeyDown={closeOnEscape}>
      <Link to="/" className={styles.brand}>
        VibeCoding
      </Link>
      <button
        type="button"
        className={styles.toggle}
        aria-expanded={isOpen}
        aria-controls={MENU_ID}
        onClick={() => {
          setOpenAt(isOpen ? null : pathname);
        }}
      >
        Меню
      </button>
      <div id={MENU_ID} className={isOpen ? [styles.menu, styles.menuOpen].join(' ') : styles.menu}>
        <nav aria-label="Разделы" className={styles.sections}>
          {SECTIONS.map((section) => (
            <NavLink
              key={section.to}
              to={section.to}
              className={() => styles.section}
              onClick={() => {
                setOpenAt(null);
              }}
            >
              {section.label}
            </NavLink>
          ))}
        </nav>
        <div className={styles.account}>
          {state.status === 'signedIn' ? <span>{state.me.name}</span> : null}
          <ErrorAlert error={signOut.error} />
          <button
            type="button"
            className={styles.signOut}
            disabled={signOut.isPending}
            onClick={() => {
              signOut.mutate();
            }}
          >
            Выйти
          </button>
        </div>
      </div>
    </header>
  );
}
