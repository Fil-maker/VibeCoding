import { Link } from 'react-router';

import { NOT_FOUND_TITLE } from '../messages';
import { Panel } from './Panel';

// The page for an address that does not exist.
export function NotFoundPage(): React.JSX.Element {
  return (
    <Panel title={NOT_FOUND_TITLE}>
      <Link to="/">На главную</Link>
    </Panel>
  );
}
