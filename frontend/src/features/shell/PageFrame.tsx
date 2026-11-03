import { useRef, type MouseEvent, type ReactNode } from 'react';

import styles from './AppShell.module.css';

const CONTENT_ID = 'content';

// The frame every page shares: the skip link first, then the header, then the content as <main>.
export function PageFrame({
  header,
  children,
}: {
  header: ReactNode;
  children: ReactNode;
}): React.JSX.Element {
  const mainRef = useRef<HTMLElement>(null);
  // A plain hash jump would not move focus in every browser and would change the URL.
  const skipToContent = (event: MouseEvent<HTMLAnchorElement>): void => {
    event.preventDefault();
    mainRef.current?.focus();
  };
  return (
    <>
      <a href={`#${CONTENT_ID}`} className={styles.skipLink} onClick={skipToContent}>
        К содержимому
      </a>
      {header}
      <main id={CONTENT_ID} tabIndex={-1} ref={mainRef} className={styles.content}>
        {children}
      </main>
    </>
  );
}
