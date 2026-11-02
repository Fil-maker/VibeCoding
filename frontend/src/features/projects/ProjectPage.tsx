import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link, useParams } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { ApiError, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { NotFoundPage } from '../../components/NotFoundPage';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { LOADING_MESSAGE } from '../../messages';
import { emailCountLabel, formatDate } from '../correspondence/format';
import { placementLabel } from './format';
import treeStyles from './ProjectPage.module.css';
import { PROJECTS_KEY } from './ProjectsPage';

type PlacedChain = components['schemas']['PlacedChain'];
type ProjectTree = components['schemas']['ProjectTree'];

const EMPTY_NEVER_FILLED_MESSAGE = 'Проект пуст: нажмите «Заполнить», чтобы найти его переписку';
const EMPTY_FILLED_MESSAGE = 'Подходящей переписки не нашлось: уточните описание';
const REFILL_QUESTION =
  'Пересобрать проект? Движок разложит его переписку заново, а цепочки, размещённые вручную, останутся на месте';
const NO_COUNTERPARTY_TITLE = 'Без контрагента';

function ChainLine({ chain }: { chain: PlacedChain }): React.JSX.Element {
  return (
    <li className={treeStyles.chain}>
      <Link to={`/chains/${chain.id}`}>{chain.subject}</Link>{' '}
      <span>
        {emailCountLabel(chain.email_count)} · {formatDate(chain.latest_email_at)} ·{' '}
        {placementLabel(chain.placement)}
      </span>
    </li>
  );
}

function Tree({ project }: { project: ProjectTree }): React.JSX.Element {
  return (
    <>
      {project.counterparties.map((counterparty) => (
        <section key={counterparty.address ?? ''} className={treeStyles.node}>
          <h2 className={styles.subheading}>
            <span>{counterparty.address === null ? NO_COUNTERPARTY_TITLE : counterparty.name}</span>
            {counterparty.address !== null && (
              <>
                {' '}
                <span className={treeStyles.address}>{counterparty.address}</span>
              </>
            )}
          </h2>
          {counterparty.threads.map((thread) => (
            <div key={thread.id} className={treeStyles.node}>
              <h3>{thread.name}</h3>
              <ul>
                {thread.chains.map((chain) => (
                  <ChainLine key={chain.id} chain={chain} />
                ))}
              </ul>
            </div>
          ))}
        </section>
      ))}
      {project.unassigned.length > 0 && (
        <section className={treeStyles.node}>
          <h2 className={styles.subheading}>Неразобранное</h2>
          <ul>
            {project.unassigned.map((chain) => (
              <ChainLine key={chain.id} chain={chain} />
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function FillControl({
  project,
  onFilled,
}: {
  project: ProjectTree;
  onFilled: (tree: ProjectTree) => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const fill = useMutation({
    mutationFn: () =>
      unwrap(
        apiClient.POST('/api/v1/projects/{project_id}/fill', {
          params: { path: { project_id: project.id } },
        }),
      ),
    onSuccess: async (tree) => {
      onFilled(tree);
      await queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
    },
    onSettled: () => {
      setConfirming(false);
    },
  });
  const hasChains = project.counterparties.length > 0 || project.unassigned.length > 0;

  return (
    <>
      <ErrorAlert error={fill.error} />
      {confirming ? (
        <div className={styles.actions}>
          <span>{REFILL_QUESTION}</span>
          <button
            type="button"
            className={styles.button}
            onClick={() => {
              fill.mutate();
            }}
          >
            Пересобрать
          </button>
          <button
            type="button"
            className={styles.button}
            onClick={() => {
              setConfirming(false);
            }}
          >
            Отмена
          </button>
        </div>
      ) : (
        <button
          type="button"
          className={styles.button}
          disabled={fill.isPending}
          onClick={() => {
            if (hasChains) {
              setConfirming(true);
            } else {
              fill.mutate();
            }
          }}
        >
          {fill.isPending ? 'Заполняется…' : 'Заполнить'}
        </button>
      )}
    </>
  );
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}

// One project: name, description, «Заполнить» and the tree of its reply chains.
export function ProjectPage(): React.JSX.Element {
  const { id = '' } = useParams();
  const queryClient = useQueryClient();
  const key = ['projects', id];
  const project = useQuery({
    queryKey: key,
    queryFn: () =>
      unwrap(
        apiClient.GET('/api/v1/projects/{project_id}', { params: { path: { project_id: id } } }),
      ),
    retry: (count, error) => !isNotFound(error) && count < 1,
  });

  if (isNotFound(project.error)) {
    return <NotFoundPage />;
  }
  if (project.data === undefined) {
    return (
      <Panel title="Проект" wide>
        <ErrorAlert error={project.error} />
        {project.isPending && <p>{LOADING_MESSAGE}</p>}
      </Panel>
    );
  }
  const tree = project.data;
  const isEmpty = tree.counterparties.length === 0 && tree.unassigned.length === 0;

  return (
    <Panel title={tree.name} wide>
      <p>
        <Link to="/projects">К проектам</Link>
      </p>
      <p className={treeStyles.description}>{tree.description}</p>
      <FillControl
        project={tree}
        onFilled={(filled) => {
          queryClient.setQueryData(key, filled);
        }}
      />
      {isEmpty && <p>{tree.filled ? EMPTY_FILLED_MESSAGE : EMPTY_NEVER_FILLED_MESSAGE}</p>}
      <Tree project={tree} />
    </Panel>
  );
}
