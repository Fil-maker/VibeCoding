import { Outlet } from 'react-router';

import { AppHeader } from './AppHeader';
import { PageFrame } from './PageFrame';

// The frame of the pages of a signed-in user: the header with the sections around the page.
export function AppLayout(): React.JSX.Element {
  return (
    <PageFrame header={<AppHeader />}>
      <Outlet />
    </PageFrame>
  );
}
