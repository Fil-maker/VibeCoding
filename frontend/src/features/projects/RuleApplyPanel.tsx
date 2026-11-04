import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LOADING_MESSAGE } from '../../messages';
import { PROJECTS_KEY } from './ProjectsPage';
import { Button } from '../../components/Button';

type RuleMove = components['schemas']['RuleMove'];

const UNASSIGNED_TITLE = 'Неразобранное';
const NO_PROJECT_TITLE = 'Вне проектов';
const APPLY_QUESTION = 'Применить правило сейчас?';
const NO_MOVES_MESSAGE = 'Подходящих цепочек нет';

function describeSource(source: RuleMove['current']): string {
  if (source.state === 'none' || source.project === null) {
    return NO_PROJECT_TITLE;
  }
  return `${source.project.name} → ${source.thread?.name ?? UNASSIGNED_TITLE}`;
}

function describeMove(move: RuleMove): string {
  const target = `${move.target.project.name} → ${move.target.thread_name ?? UNASSIGNED_TITLE}`;
  return `${move.subject}: ${describeSource(move.current)} → ${target}`;
}

// The offer to apply a rule right after it was saved: lists what would move, moves only on «Применить».
export function RuleApplyPanel({
  ruleId,
  onClose,
}: {
  ruleId: string;
  onClose: () => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const moves = useQuery({
    queryKey: ['rule-moves', ruleId],
    queryFn: () =>
      unwrap(
        apiClient.GET('/api/v1/placements/by-rule/{rule_id}', {
          params: { path: { rule_id: ruleId } },
        }),
      ),
    gcTime: 0,
  });
  const apply = useMutation({
    mutationFn: (chainIds: string[]) =>
      unwrap(
        apiClient.POST('/api/v1/placements/by-rule/{rule_id}', {
          params: { path: { rule_id: ruleId } },
          body: { chain_ids: chainIds },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: PROJECTS_KEY }),
  });

  if (apply.data !== undefined) {
    return (
      <section>
        <p>Перемещено цепочек: {apply.data.moved}</p>
        <Button onClick={onClose}>Понятно</Button>
      </section>
    );
  }

  const list = moves.data?.moves;
  return (
    <section>
      <h2>{APPLY_QUESTION}</h2>
      <ErrorAlert error={moves.error} />
      <ErrorAlert error={apply.error} />
      {moves.isPending && <p>{LOADING_MESSAGE}</p>}
      {list?.length === 0 && (
        <>
          <p>{NO_MOVES_MESSAGE}</p>
          <Button onClick={onClose}>Понятно</Button>
        </>
      )}
      {list !== undefined && list.length > 0 && (
        <>
          <ul>
            {list.map((move) => (
              <li key={move.chain_id}>{describeMove(move)}</li>
            ))}
          </ul>
          <Button
            kind="primary"
            disabled={apply.isPending}
            onClick={() => {
              apply.mutate(list.map((move) => move.chain_id));
            }}
          >
            Применить
          </Button>{' '}
          <Button disabled={apply.isPending} onClick={onClose}>
            Не сейчас
          </Button>
        </>
      )}
    </section>
  );
}
