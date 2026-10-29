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
import { StartPage } from './features/home/StartPage';
import { HealthStatus } from './features/health/HealthStatus';

const pageQueryClient = createQueryClient();

export function App({
  queryClient = pageQueryClient,
}: {
  queryClient?: QueryClient;
}): React.JSX.Element {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route element={<RequireGuest />}>
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/sign-in" element={<SignInPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            </Route>
            <Route path="/confirm-email" element={<ConfirmEmailPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/health" element={<HealthStatus />} />
            <Route element={<RequireUser />}>
              <Route path="/" element={<StartPage />} />
              <Route path="/mailboxes" element={<MailboxesPage />} />
              <Route path="/chains" element={<ChainsPage />} />
              <Route path="/chains/:id" element={<ChainPage />} />
            </Route>
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
