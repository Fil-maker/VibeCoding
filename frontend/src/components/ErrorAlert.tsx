import { errorMessage } from '../api/request';
import styles from './ui.module.css';

// Shows the message of a failed request in an alert; nothing when there is no failure.
export function ErrorAlert({ error }: { error: unknown }): React.JSX.Element | null {
  if (error === null || error === undefined) {
    return null;
  }
  return (
    <p role="alert" className={styles.error}>
      {errorMessage(error)}
    </p>
  );
}
