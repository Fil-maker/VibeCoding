import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap, unwrapEmpty } from '../../api/request';
import { Button } from '../../components/Button';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import styles from '../../components/ui.module.css';
import treeStyles from './ProjectPage.module.css';
import { PROJECTS_KEY } from './ProjectsPage';

type ProjectTree = components['schemas']['ProjectTree'];

const DESCRIPTION_CHANGED_HINT =
  'Описание изменено после заполнения: нажмите «Заполнить», чтобы пересобрать проект';

function ProjectEditForm({
  project,
  onSaved,
  onCancel,
}: {
  project: ProjectTree;
  onSaved: (tree: ProjectTree) => void;
  onCancel: () => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const save = useMutation({
    mutationFn: (body: components['schemas']['ProjectEdit']) =>
      unwrap(
        apiClient.PATCH('/api/v1/projects/{project_id}', {
          params: { path: { project_id: project.id } },
          body,
        }),
      ),
    onSuccess: async (tree) => {
      onSaved(tree);
      // The new name shows in the list, in the rules and on the pages of chains.
      await queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ['rules'] });
      await queryClient.invalidateQueries({ queryKey: ['reply-chains'] });
    },
  });
  const errors = fieldErrors(save.error);

  return (
    <form
      className={styles.form}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        save.mutate({
          name: formValue(data, 'name'),
          description: formValue(data, 'description'),
        });
      }}
    >
      <ErrorAlert error={errors.size > 0 ? null : save.error} />
      <FormField
        name="name"
        label="Название"
        defaultValue={project.name}
        error={errors.get('name')}
      />
      <FormField
        name="description"
        label="Описание"
        multiline
        defaultValue={project.description}
        error={errors.get('description')}
      />
      <div className={styles.actions}>
        <Button type="submit" kind="primary" disabled={save.isPending}>
          Сохранить
        </Button>
        <Button onClick={onCancel}>Отмена</Button>
      </div>
    </form>
  );
}

// The description with «Изменить» (and the hint of a stale filling), or the form of the edit.
export function ProjectEditing({
  project,
  onSaved,
}: {
  project: ProjectTree;
  onSaved: (tree: ProjectTree) => void;
}): React.JSX.Element {
  const [editing, setEditing] = useState(false);

  if (editing) {
    return (
      <ProjectEditForm
        project={project}
        onSaved={(tree) => {
          onSaved(tree);
          setEditing(false);
        }}
        onCancel={() => {
          setEditing(false);
        }}
      />
    );
  }
  return (
    <>
      <p className={treeStyles.description}>{project.description}</p>
      {project.description_changed && <p>{DESCRIPTION_CHANGED_HINT}</p>}
      <Button
        onClick={() => {
          setEditing(true);
        }}
      >
        Изменить
      </Button>
    </>
  );
}

function deletionQuestion(name: string, chainCount: number, ruleCount: number): string {
  return (
    `Удалить проект «${name}»? Цепочек в проекте: ${String(chainCount)} — они останутся в «Переписке» ` +
    `как убранные вручную. Правил, ведущих в проект: ${String(ruleCount)} — они будут удалены. ` +
    'Письма не удаляются.'
  );
}

// «Удалить проект»: asks with fresh counts, then deletes and leaves for «Проекты».
export function ProjectDeletion({ project }: { project: ProjectTree }): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [question, setQuestion] = useState<string | null>(null);
  const ask = useMutation({
    mutationFn: () =>
      unwrap(
        apiClient.GET('/api/v1/projects/{project_id}/deletion', {
          params: { path: { project_id: project.id } },
        }),
      ),
    onSuccess: (counts) => {
      setQuestion(deletionQuestion(project.name, counts.chain_count, counts.rule_count));
    },
  });
  const remove = useMutation({
    mutationFn: () =>
      unwrapEmpty(
        apiClient.DELETE('/api/v1/projects/{project_id}', {
          params: { path: { project_id: project.id } },
        }),
      ),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ['projects', project.id] });
      await queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
      await queryClient.invalidateQueries({ queryKey: ['rules'] });
      await queryClient.invalidateQueries({ queryKey: ['reply-chains'] });
      await navigate('/projects');
    },
  });

  if (question === null) {
    return (
      <>
        <ErrorAlert error={ask.error} />
        <Button
          kind="danger"
          disabled={ask.isPending}
          onClick={() => {
            ask.mutate();
          }}
        >
          Удалить проект
        </Button>
      </>
    );
  }
  return (
    <div>
      <p>{question}</p>
      <ErrorAlert error={remove.error} />
      <div className={styles.actions}>
        <Button
          kind="danger"
          disabled={remove.isPending}
          onClick={() => {
            remove.mutate();
          }}
        >
          Удалить
        </Button>
        <Button
          onClick={() => {
            setQuestion(null);
          }}
        >
          Отмена
        </Button>
      </div>
    </div>
  );
}
