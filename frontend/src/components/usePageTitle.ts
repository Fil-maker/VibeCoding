import { useEffect } from 'react';

const APP_NAME = 'VibeCoding';

// Sets the browser tab title: «<title> — VibeCoding», or just «VibeCoding» for null.
export function usePageTitle(title: string | null): void {
  useEffect(() => {
    document.title = title === null ? APP_NAME : `${title} — ${APP_NAME}`;
  }, [title]);
}
