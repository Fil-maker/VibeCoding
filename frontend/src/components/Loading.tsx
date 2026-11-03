import { LOADING_MESSAGE } from '../messages';

// The shared «loading» state of a page.
export function Loading(): React.JSX.Element {
  return <p role="status">{LOADING_MESSAGE}</p>;
}
