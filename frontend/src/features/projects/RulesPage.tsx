import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useId, useState } from 'react';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap, unwrapEmpty } from '../../api/request';
import { EmptyState } from '../../components/EmptyState';
import { ErrorAlert } from '../../components/ErrorAlert';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { PROJECTS_KEY } from './ProjectsPage';
import { RuleApplyPanel } from './RuleApplyPanel';
import { Button } from '../../components/Button';

type Rule = components['schemas']['Rule'];
type RuleCondition = components['schemas']['RuleCondition'];
type RuleInput = components['schemas']['RuleInput'];

export const RULES_KEY = ['rules'];

const CONDITION_TITLES: Readonly<Record<RuleCondition, string>> = {
  address: 'Адрес отправителя',
  domain: 'Домен',
  subject: 'Слова темы',
};
const CONDITIONS: readonly RuleCondition[] = ['address', 'domain', 'subject'];
const UNASSIGNED_TITLE = 'Неразобранное';
const EMPTY_RULES_MESSAGE = 'Правил пока нет';
const NO_PROJECTS_MESSAGE = 'Сначала создайте проект';
const CHOOSE_PROJECT_TITLE = 'Выберите проект';
const DELETE_QUESTION = 'Удалить правило? Цепочки, уже размещённые им, останутся на месте';

function isCondition(value: string): value is RuleCondition {
  return CONDITIONS.some((condition) => condition === value);
}

// The rule form: a new rule when `rule` is null, or an edit of one; only an edit passes `onCancel`, which adds «Отмена».
function RuleForm({
  rule,
  projects,
  submitLabel,
  onSubmit,
  onCancel,
}: {
  rule: Rule | null;
  projects: readonly { id: string; name: string }[];
  submitLabel: string;
  onSubmit: (input: RuleInput) => Promise<unknown>;
  onCancel?: () => void;
}): React.JSX.Element {
  const conditionId = useId();
  const projectId = useId();
  // Bumped after a successful creation so the uncontrolled fields start empty again.
  const [formKey, setFormKey] = useState(0);
  const save = useMutation({
    mutationFn: onSubmit,
    onSuccess: () => {
      if (rule === null) {
        setFormKey((key) => key + 1);
      }
    },
  });
  const errors = fieldErrors(save.error);
  const projectError = errors.get('project_id');

  return (
    <form
      key={formKey}
      className={styles.form}
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        const data = new FormData(event.currentTarget);
        const condition = formValue(data, 'condition');
        save.reset();
        save.mutate({
          condition: isCondition(condition) ? condition : 'address',
          value: formValue(data, 'value'),
          project_id: formValue(data, 'project_id'),
          thread_name: formValue(data, 'thread_name'),
        });
      }}
    >
      <ErrorAlert error={errors.size > 0 ? null : save.error} />
      <div className={styles.field}>
        <label htmlFor={conditionId}>Условие</label>
        <select
          id={conditionId}
          name="condition"
          className={styles.input}
          defaultValue={rule?.condition ?? 'address'}
        >
          {CONDITIONS.map((condition) => (
            <option key={condition} value={condition}>
              {CONDITION_TITLES[condition]}
            </option>
          ))}
        </select>
        {errors.get('condition') !== undefined && (
          <p className={styles.error}>{errors.get('condition')}</p>
        )}
      </div>
      <FormField
        name="value"
        label="Значение"
        defaultValue={rule?.value ?? ''}
        error={errors.get('value')}
      />
      <div className={styles.field}>
        <label htmlFor={projectId}>Проект</label>
        <select
          id={projectId}
          name="project_id"
          className={styles.input}
          defaultValue={rule?.project.id ?? ''}
        >
          <option value="">{CHOOSE_PROJECT_TITLE}</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
        {projectError !== undefined && <p className={styles.error}>{projectError}</p>}
      </div>
      <div className={styles.field}>
        <label htmlFor={`${projectId}-thread`}>Ветка</label>
        <input
          id={`${projectId}-thread`}
          name="thread_name"
          type="text"
          placeholder={UNASSIGNED_TITLE}
          defaultValue={rule?.thread_name ?? ''}
          className={styles.input}
        />
        {errors.get('thread_name') !== undefined && (
          <p className={styles.error}>{errors.get('thread_name')}</p>
        )}
      </div>
      <div>
        <Button type="submit" kind="primary" disabled={save.isPending}>
          {submitLabel}
        </Button>
        {onCancel !== undefined && <Button onClick={onCancel}>Отмена</Button>}
      </div>
    </form>
  );
}

// One listed rule in view, edit or delete mode: «Изменить» edits it in place, «Удалить» asks before it deletes.
function RuleLine({
  rule,
  projects,
  onSaved,
}: {
  rule: Rule;
  projects: readonly { id: string; name: string }[];
  onSaved: (ruleId: string) => void;
}): React.JSX.Element {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<'view' | 'edit' | 'delete'>('view');
  const remove = useMutation({
    mutationFn: () =>
      unwrapEmpty(
        apiClient.DELETE('/api/v1/rules/{rule_id}', { params: { path: { rule_id: rule.id } } }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: RULES_KEY }),
  });

  if (mode === 'edit') {
    return (
      <li>
        <RuleForm
          rule={rule}
          projects={projects}
          submitLabel="Сохранить"
          onSubmit={async (body) => {
            const saved = await unwrap(
              apiClient.PUT('/api/v1/rules/{rule_id}', {
                params: { path: { rule_id: rule.id } },
                body,
              }),
            );
            await queryClient.invalidateQueries({ queryKey: RULES_KEY });
            setMode('view');
            onSaved(saved.id);
            return saved;
          }}
          onCancel={() => {
            setMode('view');
          }}
        />
      </li>
    );
  }
  return (
    <li>
      <span>
        {CONDITION_TITLES[rule.condition]}: {rule.value} → {rule.project.name} →{' '}
        {rule.thread_name ?? UNASSIGNED_TITLE}
      </span>{' '}
      {mode === 'view' ? (
        <>
          <Button
            onClick={() => {
              setMode('edit');
            }}
          >
            Изменить
          </Button>{' '}
          <Button
            onClick={() => {
              setMode('delete');
            }}
          >
            Удалить
          </Button>
        </>
      ) : (
        <>
          <p>{DELETE_QUESTION}</p>
          <ErrorAlert error={remove.error} />
          <Button
            kind="danger"
            disabled={remove.isPending}
            onClick={() => {
              remove.mutate();
            }}
          >
            Удалить
          </Button>{' '}
          <Button
            onClick={() => {
              setMode('view');
            }}
          >
            Отмена
          </Button>
        </>
      )}
    </li>
  );
}

// «Правила»: the form of a new rule and the user's rules in the order they win.
export function RulesPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  // The nonce restarts the panel when the same rule is saved twice.
  const [offer, setOffer] = useState<{ ruleId: string; nonce: number } | null>(null);
  const offerApply = (ruleId: string): void => {
    setOffer((previous) => ({ ruleId, nonce: (previous?.nonce ?? 0) + 1 }));
  };
  const rules = useQuery({
    queryKey: RULES_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/rules')),
  });
  const projects = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/projects')),
  });

  return (
    <Panel title="Правила" wide>
      <LoadError error={rules.error} onRetry={() => void rules.refetch()} />
      <LoadError error={projects.error} onRetry={() => void projects.refetch()} />
      {projects.isPending && <Loading />}
      {projects.data?.length === 0 && (
        <EmptyState
          message={NO_PROJECTS_MESSAGE}
          action={{ to: '/projects/new', label: 'Создать проект' }}
        />
      )}
      {projects.data !== undefined && projects.data.length > 0 && (
        <RuleForm
          rule={null}
          projects={projects.data}
          submitLabel="Создать правило"
          onSubmit={async (body) => {
            const created = await unwrap(apiClient.POST('/api/v1/rules', { body }));
            await queryClient.invalidateQueries({ queryKey: RULES_KEY });
            offerApply(created.id);
            return created;
          }}
        />
      )}
      {offer !== null && (
        <RuleApplyPanel
          key={offer.nonce}
          ruleId={offer.ruleId}
          onClose={() => {
            setOffer(null);
          }}
        />
      )}
      {rules.isPending && <Loading />}
      {rules.data?.length === 0 && <p>{EMPTY_RULES_MESSAGE}</p>}
      {rules.data !== undefined && rules.data.length > 0 && (
        <ul>
          {rules.data.map((rule) => (
            <RuleLine
              key={rule.id}
              rule={rule}
              projects={projects.data ?? []}
              onSaved={offerApply}
            />
          ))}
        </ul>
      )}
    </Panel>
  );
}
