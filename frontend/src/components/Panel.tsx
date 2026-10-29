import type { ReactNode } from 'react';

import styles from './ui.module.css';

interface PanelProps {
  title: string;
  wide?: boolean;
  children: ReactNode;
}

// A page card: the page title is its only <h1>.
export function Panel({ title, wide = false, children }: PanelProps): React.JSX.Element {
  return (
    <main className={wide ? [styles.panel, styles.wide].join(' ') : styles.panel}>
      <h1 className={styles.heading}>{title}</h1>
      {children}
    </main>
  );
}
