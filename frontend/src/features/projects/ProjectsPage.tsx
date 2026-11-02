import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { ErrorAlert } from '../../components/ErrorAlert';
import { Panel } from '../../components/Panel';
import styles from '../../components/ui.module.css';
import { LOADING_MESSAGE } from '../../messages';
import { chainCountLabel, unassignedCountLabel } from './format';

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
      <p>
        <Link to="/">На главную</Link>
      </p>
      <ErrorAlert error={projects.error} />
      {projects.isPending && <p>{LOADING_MESSAGE}</p>}
      {projects.data?.length === 0 && <p>{EMPTY_PROJECTS_MESSAGE}</p>}
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
      <button
        type="button"
        className={styles.button}
        onClick={() => {
          void navigate('/projects/new');
        }}
      >
        Создать проект
      </button>
    </Panel>
  );
}
