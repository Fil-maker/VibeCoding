import { LOADING_MESSAGE, SERVER_UNAVAILABLE_MESSAGE } from '../messages';
import { Panel } from './Panel';

// The page while the session loads or the server is unavailable; the tab reads plain «VibeCoding».
export function Waiting({ failed }: { failed: boolean }): React.JSX.Element {
  return (
    <Panel title="VibeCoding" tabTitle={null}>
      {failed ? <p role="alert">{SERVER_UNAVAILABLE_MESSAGE}</p> : <p>{LOADING_MESSAGE}</p>}
    </Panel>
  );
}
