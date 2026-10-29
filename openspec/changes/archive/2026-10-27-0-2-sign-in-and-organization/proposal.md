# Proposal

## Why

The product promises that an employee sees only their own correspondence and the administrator all
correspondence of their organization (`docs/prd.md` «Users», «Product principles»). Nothing in the app
knows who a user is or which organization they belong to, so no mailbox, email or assessment can have
an owner yet. Plan task 0.2 «Sign-in and organization» gives the app real organizations, users and
roles before «Mailbox connection» needs them. A built-in stub user would mean reworking the owner
filter in every query later.

## What Changes

- An organization registers itself on the page «Регистрация». The registrant confirms their email by a
  link and becomes the organization's first administrator. One installation serves many organizations.
  An email belongs to one user in one organization.
- Users sign in with email and password and sign out. A session lives on the server and ends on
  sign-out, on expiry, on deactivation and on a password reset. Five wrong passwords in 15 minutes lock
  sign-in for that email for 15 minutes.
- A forgotten password is reset by a single-use emailed link valid for 1 hour.
- An administrator invites an employee by email. An invitation is single-use, expires after 7 days and
  can be revoked. When the email could not be sent, the invitation shows «Не отправлено» and can be sent
  again. An employee joins only by invitation.
- The administrator sees the members of the organization, deactivates and reactivates an employee (their
  data is kept), and appoints or removes administrators. The last active administrator cannot be
  removed or deactivated.
- Every request after sign-in carries the user's organization and role. Data of another organization
  answers «not found». Employees get «not found» for the administrator's actions.
- The app sends its own service emails (confirmation, invitation, password reset) through SMTP. In
  development Mailpit catches them; tests use a fake sender.
- The SPA gets the pages «Регистрация», «Вход», «Восстановление пароля», «Новый пароль», «Приглашение»
  and «Участники», and a guard that sends a signed-out visitor to «Вход».

## Capabilities

### New Capabilities

- `organization-registration`: an organization registers itself, and the registrant confirms their email and
  becomes the first administrator.
- `sign-in`: sign-in with email and password, sessions, sign-out, the lock after failed attempts,
  password reset by email.
- `invitations`: the administrator invites employees by email; delivery status, resending, revoking,
  expiry and acceptance.
- `organization-members`: the members list, deactivation and reactivation, the administrator role and
  the last-administrator guard.
- `access-boundary`: every protected request needs a signed-in user. Data is scoped to the user's
  organization. Administrator-only actions are closed to employees.

### Modified Capabilities

None. No specs exist yet.

## Out of scope

- Sign-in through external identity providers (Yandex ID, Google): dropped by the user's decision.
- Changing the password or the email while signed in, editing the name, deleting an organization or a
  user. Recorded in `docs/ideas.md` «Account settings».
- Two-factor authentication, a CAPTCHA, and rate limits by IP beyond the per-email lock. Recorded in
  `docs/ideas.md` «Account settings».
- The owner filter over correspondence. This change provides the auth context with the organization,
  the user and the role. «Mailbox connection» applies it to the first owned data.

## Invariants touched

- **Access boundary** is implemented, not changed. Organization isolation and the employee versus
  administrator split are introduced here and specified in `access-boundary`.
- **History is kept**: deactivating an employee keeps their data and history; nothing is deleted.
- **Mailbox read-only** is not touched. The app's service emails go through its own SMTP account, never
  through a user's mailbox. `docs/domain.md` «Data and privacy» says so explicitly.

## Impact

- Backend: new modules `organizations` (registration, members), `auth` (sign-in, sessions, password
  reset) and `invitations`; platform additions: the auth context dependency, the password hasher, the
  mail sender, the Origin check, structured errors.
- Database: the first tables and the Alembic revision `0002`.
- API: new routes under `/api/v1/auth`, `/api/v1/organizations`, `/api/v1/invitations`,
  `/api/v1/members`; the regenerated SPA client.
- SPA: routing, the auth state, six pages.
- Dependencies, approved by the user: `argon2-cffi`, `aiosmtplib`, and the Mailpit service in
  `docker-compose.yml`. The SPA routing library still needs the user's approval: `react-router`, see the
  design.
- Env vars: SMTP settings, the public base URL for links, and the lifetimes and limits with defaults.
