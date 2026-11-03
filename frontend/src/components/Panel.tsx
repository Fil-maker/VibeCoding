import type { ReactNode } from 'react';

import styles from './ui.module.css';
import { usePageTitle } from './usePageTitle';

interface PanelProps {
  title: string;
  // The tab title; by default the page title, null for plain «VibeCoding».
  tabTitle?: string | null;
  wide?: boolean;
  children: ReactNode;
}

// A page card: the page title is its only <h1>; the frame supplies <main>.
export function Panel({
  title,
  tabTitle = title,
  wide = false,
  children,
}: PanelProps): React.JSX.Element {
  usePageTitle(tabTitle);
  return (
    <section className={wide ? [styles.panel, styles.wide].join(' ') : styles.panel}>
      <h1 className={styles.heading}>{title}</h1>
      {children}
    </section>
  );
}
