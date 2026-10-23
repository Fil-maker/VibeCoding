import styles from './HealthStatus.module.css';
import { useHealth } from './useHealth';

// The health page: shows the server and database state read from GET /api/v1/health.
export function HealthStatus(): React.JSX.Element {
  const health = useHealth();
  const isDatabaseOk = health.data?.database === 'ok';

  return (
    <section className={styles.panel}>
      <h1 className={styles.heading}>Состояние сервиса</h1>
      {health.isPending && <p className={styles.muted}>Проверяем…</p>}
      {health.isError && <p className={styles.danger}>Сервер не отвечает</p>}
      {health.isSuccess && (
        <ul className={styles.list}>
          <li className={[styles.item, styles.ok].join(' ')}>Сервер: работает</li>
          <li className={[styles.item, isDatabaseOk ? styles.ok : styles.danger].join(' ')}>
            {isDatabaseOk ? 'База данных: доступна' : 'База данных: недоступна'}
          </li>
        </ul>
      )}
    </section>
  );
}
