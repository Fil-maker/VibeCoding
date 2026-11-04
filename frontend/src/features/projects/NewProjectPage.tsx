import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';

import { apiClient } from '../../api/client';
import type { components } from '../../api/generated/schema';
import { fieldErrors, unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { formValue } from '../../components/formData';
import { FormField } from '../../components/FormField';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { PROJECTS_KEY } from './ProjectsPage';
import { Button } from '../../components/Button';

// «Новый проект»: the name and the description; success opens the project.
export function NewProjectPage(): React.JSX.Element {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const create = useMutation({
    mutationFn: (body: components['schemas']['ProjectCreate']) =>
      unwrap(apiClient.POST('/api/v1/projects', { body })),
    onSuccess: async (project) => {
      await queryClient.invalidateQueries({ queryKey: PROJECTS_KEY });
      await navigate(`/projects/${project.id}`);
    },
  });
  const errors = fieldErrors(create.error);

  return (
    <Panel title="Новый проект">
      <p>
        <Link to="/projects">К проектам</Link>
      </p>
      <form
        className={styles.form}
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          const data = new FormData(event.currentTarget);
          create.mutate({
            name: formValue(data, 'name'),
            description: formValue(data, 'description'),
          });
        }}
      >
        <ErrorAlert error={errors.size > 0 ? null : create.error} />
        <FormField name="name" label="Название" error={errors.get('name')} />
        <FormField
          name="description"
          label="Описание"
          multiline
          error={errors.get('description')}
        />
        <Button type="submit" kind="primary" disabled={create.isPending}>
          Создать
        </Button>
      </form>
    </Panel>
  );
}
