import { errorMessage } from '../api/request';
import styles from './ui.module.css';

// The shared state of a page whose data failed to load: the reason and a retry in one alert.
export function LoadError({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry: () => void;
}): React.JSX.Element | null {
  if (error === null || error === undefined) {
    return null;
  }
  return (
    <div role="alert" className={styles.error}>
      <p>{errorMessage(error)}</p>
      <button type="button" className={styles.button} onClick={onRetry}>
        Повторить
      </button>
    </div>
  );
}
