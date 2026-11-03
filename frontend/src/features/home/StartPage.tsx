import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, Navigate } from 'react-router';

import { apiClient } from '../../api/client';
import { unwrap } from '../../api/request';
import { Loading } from '../../components/Loading';
import { LoadError } from '../../components/LoadError';
import { Panel } from '../../components/Panel';
import { MAILBOXES_KEY } from '../mailboxes/MailboxesPage';
import { PROJECTS_KEY } from '../projects/ProjectsPage';

interface Step {
  label: string;
  to: string;
  isDone: boolean;
}

// The start page of a signed-in user: the first steps, or «Проекты» once all are done.
export function StartPage(): React.JSX.Element {
  const mailboxes = useQuery({
    queryKey: MAILBOXES_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/mailboxes')),
  });
  const projects = useQuery({
    queryKey: PROJECTS_KEY,
    queryFn: () => unwrap(apiClient.GET('/api/v1/projects')),
  });

  if (mailboxes.data === undefined || projects.data === undefined) {
    const error = mailboxes.error ?? projects.error;
    // No heading while loading: «Первые шаги» appears together with the steps.
    if (error === null) {
      return <Loading />;
    }
    return (
      <StartFrame>
        <LoadError
          error={error}
          onRetry={() => {
            void mailboxes.refetch();
            void projects.refetch();
          }}
        />
      </StartFrame>
    );
  }

  const firstNotFilled = projects.data.find((project) => !project.filled);
  const steps: Step[] = [
    { label: 'Подключите почтовый ящик', to: '/mailboxes', isDone: mailboxes.data.length > 0 },
    { label: 'Создайте проект', to: '/projects/new', isDone: projects.data.length > 0 },
    {
      label: 'Заполните проект',
      to: firstNotFilled === undefined ? '/projects' : `/projects/${firstNotFilled.id}`,
      isDone: projects.data.some((project) => project.filled),
    },
  ];
  if (steps.every((step) => step.isDone)) {
    return <Navigate to="/projects" replace />;
  }
  return (
    <StartFrame>
      <ol>
        {steps.map((step) => (
          <li key={step.label}>
            {step.isDone ? (
              <>
                <span>{step.label}</span> <span>Готово</span>
              </>
            ) : (
              <Link to={step.to}>{step.label}</Link>
            )}
          </li>
        ))}
      </ol>
    </StartFrame>
  );
}

// The tab of the start page reads plain «VibeCoding».
function StartFrame({ children }: { children: ReactNode }): React.JSX.Element {
  return (
    <Panel title="Первые шаги" tabTitle={null}>
      {children}
    </Panel>
  );
}
