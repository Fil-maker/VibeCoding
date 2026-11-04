import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { EmptyState } from '../../components/EmptyState';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { chainCountLabel, unassignedCountLabel } from './format';
import { Button } from '../../components/Button';

export const PROJECTS_KEY = ['projects'];

const EMPTY_PROJECTS_MESSAGE = 'Проектов пока нет: создайте первый';

// «Проекты»: the user's projects by name with their chain counts.
export function ProjectsPage(): React.JSX.Element {
  const navigate = useNavigate();
  const projects = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/projects')),
  });

  return (
    <Panel title="Проекты" wide>
      <LoadError error={projects.error} onRetry={() => void projects.refetch()} />
      {projects.isPending && <Loading />}
      {projects.data?.length === 0 && (
        <EmptyState
          message={EMPTY_PROJECTS_MESSAGE}
          action={{ to: '/projects/new', label: 'Создать проект' }}
        />
      )}
      {projects.data !== undefined && projects.data.length > 0 && (
        <table className={styles.table}>
          <tbody>
            {projects.data.map((project) => (
              <tr key={project.id}>
                <td>
                  <Link to={`/projects/${project.id}`}>{project.name}</Link>
                </td>
                <td>{chainCountLabel(project.placed_count)}</td>
                <td>
                  {project.unassigned_count > 0 && unassignedCountLabel(project.unassigned_count)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {projects.data !== undefined && projects.data.length > 0 && (
        <Button
          onClick={() => {
            void navigate('/projects/new');
          }}
        >
          Создать проект
        </Button>
      )}
    </Panel>
  );
}
