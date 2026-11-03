// Root component: the query client, the router and the one auth provider; the routes of the SPA.
import { QueryClientProvider, type QueryClient } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router';

import { createQueryClient } from './api/queryClient';
import { NotFoundPage } from './components/NotFoundPage';
import { AuthProvider } from './features/auth/AuthProvider';
import { ConfirmEmailPage } from './features/auth/ConfirmEmailPage';
import { ForgotPasswordPage } from './features/auth/ForgotPasswordPage';
import { RequireGuest, RequireUser } from './features/auth/guards';
import { RegisterPage } from './features/auth/RegisterPage';
import { ResetPasswordPage } from './features/auth/ResetPasswordPage';
import { SignInPage } from './features/auth/SignInPage';
import { ChainPage } from './features/correspondence/ChainPage';
import { ChainsPage } from './features/correspondence/ChainsPage';
import { MailboxesPage } from './features/mailboxes/MailboxesPage';
import { NewProjectPage } from './features/projects/NewProjectPage';
import { ProjectPage } from './features/projects/ProjectPage';
import { ProjectsPage } from './features/projects/ProjectsPage';
import { RulesPage } from './features/projects/RulesPage';
import { HomeRoute } from './features/home/HomeRoute';
import { HealthStatus } from './features/health/HealthStatus';
import { AppLayout } from './features/shell/AppLayout';
import { AuthFrame } from './features/shell/AuthFrame';
import { GuestLayout } from './features/shell/GuestLayout';

const pageQueryClient = createQueryClient();

export function App({
  queryClient = pageQueryClient,
}: {
  queryClient?: QueryClient;
}): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      {/* Plain updates, not transitions: sign-out must commit the move to «/» synchronously (AppHeader). */}
      <BrowserRouter useTransitions={false}>
        <AuthProvider>
          <Routes>
            <Route element={<RequireGuest />}>
              <Route element={<GuestLayout />}>
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/sign-in" element={<SignInPage />} />
                <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              </Route>
            </Route>
            <Route element={<GuestLayout />}>
              <Route path="/confirm-email" element={<ConfirmEmailPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
            </Route>
            <Route path="/health" element={<HealthStatus />} />
            <Route element={<RequireUser />}>
              <Route element={<AppLayout />}>
                <Route path="/mailboxes" element={<MailboxesPage />} />
                <Route path="/chains" element={<ChainsPage />} />
                <Route path="/chains/:id" element={<ChainPage />} />
                <Route path="/projects" element={<ProjectsPage />} />
                <Route path="/projects/new" element={<NewProjectPage />} />
                <Route path="/projects/:id" element={<ProjectPage />} />
                <Route path="/rules" element={<RulesPage />} />
              </Route>
            </Route>
            <Route element={<AuthFrame />}>
              <Route path="/" element={<HomeRoute />} />
              <Route path="*" element={<NotFoundPage />} />
            </Route>
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
