import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { Link } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import styles from '../../components/ui.module.css';
import { LOADING_MESSAGE } from '../../messages';
import { placementLabel } from './format';
import { PROJECTS_KEY } from './ProjectsPage';

type ChainLocation = components['schemas']['ChainLocation'];

const UNASSIGNED_TITLE = 'Неразобранное';
const NO_PROJECT_TEXT = 'Вне проектов';
const EXCLUDED_TEXT = 'Вне проектов · убрана вручную';
// Option values of the «Ветка» select that are not thread ids.
const UNASSIGNED_VALUE = '';
const NEW_THREAD_VALUE = 'new';

function LocationText({ location }: { location: ChainLocation }): React.JSX.Element {
  if (location.state === 'excluded') {
    return <>{EXCLUDED_TEXT}</>;
  }
  if (location.project === null || location.placement === null) {
    return <>{NO_PROJECT_TEXT}</>;
  }
  return (
    <>
      <Link to={`/projects/${location.project.id}`}>{location.project.name}</Link> →{' '}
      {location.thread === null ? UNASSIGNED_TITLE : location.thread.name} ·{' '}
      {placementLabel(location.placement)}
    </>
  );
}

function MoveForm({
  chainId,
  location,
  onMoved,
}: {
  chainId: string;
  location: ChainLocation;
  onMoved: (location: ChainLocation) => Promise<void>;
}): React.JSX.Element {
  const projectId = useId();
  const threadId = useId();
  const [chosenProject, setChosenProject] = useState<string | null>(null);
  const [chosenThread, setChosenThread] = useState<string | null>(null);
  const projects = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/projects')),
  });
  const project = chosenProject ?? location.project?.id ?? projects.data?.[0]?.id ?? '';
  // The thread starts at the chain's own one while its own project is selected, so an untouched
  // form does not pull the chain out of its thread.
  const thread =
    chosenThread ??
    (project === location.project?.id ? location.thread?.id : undefined) ??
    UNASSIGNED_VALUE;
  const threads = useQuery({
    queryKey: ['projects', project, 'threads'],
    queryFn: () =>
      unwrap(
        apiClient.GET('/api/v1/projects/{project_id}/threads', {
          params: { path: { project_id: project } },
        }),
      ),
    enabled: project !== '',
  });
  const move = useMutation({
    mutationFn: (body: components['schemas']['PlacementMove']) =>
      unwrap(
        apiClient.PUT('/api/v1/placements/{chain_id}', {
          params: { path: { chain_id: chainId } },
          body,
        }),
      ),
    onSuccess: onMoved,
  });
  const errors = fieldErrors(move.error);

  const isNewThread = thread === NEW_THREAD_VALUE;

  return (
    <form
      className={styles.form}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        move.mutate({
          project_id: project,
          thread_id: thread === UNASSIGNED_VALUE || isNewThread ? null : thread,
          new_thread_name: isNewThread ? formValue(data, 'new_thread_name') : null,
        });
      }}
    >
      <h3>Перенести</h3>
      <ErrorAlert error={projects.error} />
      <ErrorAlert error={errors.size > 0 ? null : move.error} />
      <div className={styles.field}>
        <label htmlFor={projectId}>Проект</label>
        <select
          id={projectId}
          className={styles.input}
          value={project}
          onChange={(event) => {
            setChosenProject(event.target.value);
            setChosenThread(UNASSIGNED_VALUE);
          }}
        >
          {projects.data?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </div>
      <div className={styles.field}>
        <label htmlFor={threadId}>Ветка</label>
        <select
          id={threadId}
          className={styles.input}
          value={thread}
          onChange={(event) => {
            setChosenThread(event.target.value);
          }}
        >
          <option value={UNASSIGNED_VALUE}>{UNASSIGNED_TITLE}</option>
          {threads.data?.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
          <option value={NEW_THREAD_VALUE}>Новая ветка…</option>
        </select>
        {!isNewThread && errors.get('thread_id') !== undefined && (
          <p className={styles.error}>{errors.get('thread_id')}</p>
        )}
      </div>
      {isNewThread && (
        <FormField
          name="new_thread_name"
          label="Название ветки"
          error={errors.get('new_thread_name') ?? errors.get('thread_id')}
        />
      )}
      <button type="submit" className={styles.button} disabled={move.isPending}>
        Перенести
      </button>
    </form>
  );
}

// The «Проект» block of a chain page: where the chain is, the form «Перенести» and «Убрать из проекта».
export function ChainPlacement({ chainId }: { chainId: string }): React.JSX.Element {
  const queryClient = useQueryClient();
  const key = ['placements', chainId];
  const location = useQuery({
    queryKey: key,
    queryFn: () =>
      unwrap(
        apiClient.GET('/api/v1/placements/{chain_id}', { params: { path: { chain_id: chainId } } }),
      ),
  });
  const changed = async (next: ChainLocation): Promise<void> => {
    queryClient.setQueryData(key, next);
    await queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
  };
  const takeOut = useMutation({
    mutationFn: () =>
      unwrap(
        apiClient.DELETE('/api/v1/placements/{chain_id}', {
          params: { path: { chain_id: chainId } },
        }),
      ),
    onSuccess: changed,
  });

  return (
    <section>
      <h2 className={styles.subheading}>Проект</h2>
      <ErrorAlert error={location.error} />
      {location.isPending && <p>{LOADING_MESSAGE}</p>}
      {location.data !== undefined && (
        <>
          <p>
            <LocationText location={location.data} />
          </p>
          <ErrorAlert error={takeOut.error} />
          {location.data.state === 'placed' && (
            <button
              type="button"
              className={styles.button}
              disabled={takeOut.isPending}
              onClick={() => {
                takeOut.mutate();
              }}
            >
              Убрать из проекта
            </button>
          )}
          <MoveForm chainId={chainId} location={location.data} onMoved={changed} />
        </>
      )}
    </section>
  );
}
