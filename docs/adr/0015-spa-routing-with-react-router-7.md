# SPA routing with react-router 7 in declarative mode

Id: 0015 · Date: 23.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 0.2.
- Task 0.2 built three backend modules: accounts (registration, email confirmation, members list, deactivate/reactivate, role change; its router.py holds two APIRouters, /api/v1/auth registration+confirmation and /api/v1/members), auth (sign-in, sign-in lock, server-side sessions with the vc_session cookie, sign-out, GET /auth/me, password reset, the current_user and current_admin dependencies in auth/dependencies.py), invitations (invite, list, resend, revoke, preview, accept).
- New tables in migration 0002_accounts_auth_invitations: organizations, users, sessions, user_tokens (email confirmation and password reset links), invitations, sign_in_failures; ids are UUID, timestamps timestamptz, child rows cascade on delete; only SHA-256 hashes of session, link and invitation tokens are stored; passwords are Argon2id hashes.
- Domain errors carry no HTTP status: each router declares an ERROR_MAPPING from domain error classes to platform.errors.HttpError(status_code, code, message) and registers it with register_domain_errors; responses have the shape {code, message, fields}; 422 is mapped to validation_failed with Russian field messages.
- platform additions: errors.py, origin.py (middleware refusing state-changing requests whose Origin is missing or differs from APP_BASE_URL), passwords.py (Argon2id in a worker thread, dummy verify for unknown emails, rehash flag), mail.py (MailSender protocol, SmtpMailSender over aiosmtplib with a timeout, FakeMailSender for tests, get_mail_sender dependency), tokens.py, validation.py, pagination.py (keyset pages by limit and cursor; a bad cursor answers 400 invalid_cursor), auth_context.py (AuthContext with user id, organization id and role), clock.get_clock (lazy SystemClock dependency).
- Access boundary: every member and invitation query filters by the organization from the session's AuthContext; administrator routes answer 404 «Не найдено» to employees and to other organizations; request bodies forbid extra fields so organization_id cannot be sent; the last-active-administrator guard locks the organization row (SELECT FOR UPDATE).
- Emails are sent after the database commit; an invitation's delivery (sent / not_sent) is written in a second transaction, so an SMTP failure leaves the invitation «Не отправлено» and resendable.
- Dev stack: docker-compose gained the mailpit service (axllent/mailpit:v1.29, SMTP 1025 inside the network, web UI on host port 8025); the backend container gets SMTP_HOST=mailpit, APP_BASE_URL=http://localhost:5173 and MAIL_FROM from .env; the backend command runs uv sync --frozen --no-install-project before alembic upgrade head, because the named venv volume is filled from the image only once.
- New settings (env vars): APP_BASE_URL, MAIL_FROM, SMTP_HOST (required); SMTP_PORT=1025, SMTP_USERNAME, SMTP_PASSWORD, SMTP_STARTTLS=false, SESSION_COOKIE_SECURE=false, SESSION_LIFETIME_DAYS=14, CONFIRMATION_LINK_HOURS=24, PASSWORD_RESET_LINK_MINUTES=60, INVITATION_LIFETIME_DAYS=7, SIGN_IN_MAX_FAILURES=5, SIGN_IN_FAILURE_WINDOW_MINUTES=15, SIGN_IN_LOCK_MINUTES=15 (defaults; source of truth backend/app/platform/settings.py and .env.example).
- New dependencies: backend argon2-cffi and aiosmtplib; frontend react-router 7 (declarative mode).
- SPA: BrowserRouter routes /register, /sign-in, /forgot-password, /confirm-email, /reset-password, /invitation, /health (the health page moved from / to /health), / (start page, signed in), /members (administrator only), * (Страница не найдена). AuthProvider (features/auth) is the one place that knows who is signed in (GET /auth/me via TanStack Query) and exports isAdministrator; guards RequireUser (to /sign-in?next=…), RequireAdmin (Страница не найдена for employees), RequireGuest. Link tokens are read from the URL fragment #token= (urlToken.ts). api/request.ts unwraps the openapi-fetch result into data or an ApiError; messages.ts holds the UI texts the server does not send; components/ holds Panel, FormField, ErrorAlert, NotFoundPage and ui.module.css on the tokens of styles/tokens.css.
- Tests: backend integration tests per FR group through the HTTP API on real PostgreSQL with get_mail_sender and get_clock overridden (tests/factories.py, settable_clock.py, members_api.py, invitations_api.py, alembic_runner.py for the migration round trip); SPA tests App.<area>.test.tsx render <App queryClient> with fetch stubbed (src/test/appHarness.tsx, membersFixtures.tsx).
- .gitattributes sets '* text=auto eol=lf': every working copy uses LF, which Prettier, ruff and the hooks expect.
- Implementation status: task 0.2 Sign-in and organization is done (✅).

## Decision
SPA routing with react-router 7 in declarative mode

## Alternatives
TanStack Router; a hand-written router over the History API

## Reason
Approved by the user as recommended
