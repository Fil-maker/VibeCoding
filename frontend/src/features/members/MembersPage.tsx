import { Panel } from '../../components/Panel';
import { InvitationsSection } from './InvitationsSection';
import { MembersSection } from './MembersSection';

// «Участники»: the members of the organization and its invitations. Reached through RequireAdmin.
export function MembersPage(): React.JSX.Element {
  return (
    <Panel title="Участники" wide>
      <MembersSection />
      <InvitationsSection />
    </Panel>
  );
}
