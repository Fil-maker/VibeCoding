import { Link } from 'react-router';

import styles from '../../components/ui.module.css';
import { usePageTitle } from '../../components/usePageTitle';
import shell from '../shell/AppShell.module.css';

// What a guest sees at «/»: what the app does in three steps; it reads no user data.
export function LandingPage(): React.JSX.Element {
  usePageTitle(null);
  return (
    <section className={styles.panel}>
      <h1 className={styles.heading}>Переписка по проектам — в одном дереве</h1>
      <p className={shell.lead}>
        VibeCoding собирает письма из всех ваших ящиков и раскладывает их по проектам: проект →
        контрагент → ветка.
      </p>
      <ol className={shell.steps}>
        <li>Подключите почтовые ящики — только для чтения</li>
        <li>Опишите проект в нескольких предложениях</li>
        <li>Получите дерево переписки — и объяснение, почему каждая цепочка на своём месте</li>
      </ol>
      <p className={shell.cta}>
        <Link to="/register">Зарегистрироваться</Link>
        <Link to="/sign-in">Войти</Link>
      </p>
    </section>
  );
}
