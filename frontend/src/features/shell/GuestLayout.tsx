import { Link, Outlet } from 'react-router';

import styles from './AppShell.module.css';
import { PageFrame } from './PageFrame';

// The frame of the pages a signed-out visitor sees: only the name of the app, leading to «/».
export function GuestLayout(): React.JSX.Element {
  return (
    <PageFrame
      header={
        <header className={styles.header}>
          <Link to="/" className={styles.brand}>
            VibeCoding
          </Link>
        </header>
      }
    >
      <Outlet />
    </PageFrame>
  );
}
