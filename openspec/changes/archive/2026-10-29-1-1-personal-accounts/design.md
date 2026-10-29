# Design

## Context

Task 0.2 built accounts on top of organizations: `organizations` is the root table, and `users`,
`sessions` and `user_tokens` carry `organization_id`. Users have `role` (administrator or employee)
and `is_active`. The `invitations` module owns the `invitations` table, and the `accounts` module
serves the members routes. The auth context in `app/platform` holds `user_id`, `organization_id` and
`role`, and every repository filters by `organization_id`. The SPA has the pages «Участники» and
invitation acceptance and an administrator guard. See proposal.md «Why» for the motivation.

## Goals / Non-Goals

**Goals:**
- The user is the root owner: the auth context holds the user only, and owner-scoped queries filter
  by `user_id`.
- No organization, role, deactivation or invitation code is left in the backend, the SPA, the API or
  the schema.
- Existing users keep signing in with their old email and password.

**Non-Goals:**
- The owner filter of mailboxes, chains and projects (they don't exist yet; the data-access rule
  describes it for them).
- Renaming the spec folders `organization-registration` and `access-boundary`.

## Decisions

### Existing users become individual accounts

The migration drops `organizations`, `invitations`, the `organization_id` columns of `users`,
`sessions` and `user_tokens`, and `users.role` and `users.is_active`. Users, their password hashes,
confirmation, sessions and open tokens stay as they are. A formerly deactivated user can sign in again.
Decided by the user.

Alternatives: delete every user, so everyone registers again (dev accounts are lost for nothing);
keep only confirmed users (an unconfirmed registration is already replaced by FR-3 on the next
attempt, so deleting it gains nothing).

### Deactivation goes away with the administrators

`is_active`, the `account_disabled` error and the deactivated branches of sign-in and password reset
are removed. Decided by the user: deactivation was an administrator's action, and nobody is left to
perform it. Blocking an account, if needed, comes back as its own idea.

Alternative: keep the flag with nobody able to change it — dead state in every sign-in check.

### FR-18 is replaced by FR-21

FR-18's scenarios were about organizations and an administrator; they cannot be kept under the same
number with the same scenario names, and the project rule replaces a requirement whose scenarios go
away. FR-18 is removed and FR-21 «Users never see each other» states the per-user boundary. FR-1 keeps
its number with the new name «Register a user».

Alternative: keep FR-18 with rewritten scenarios under the old names — the names would lie, and
`openspec validate` refuses a MODIFIED block that drops scenarios.

### The spec folders keep their names; their Purpose is rewritten at archive

The capability folders `organization-registration`, `sign-in` and `access-boundary` stay; `/finish`
rewrites their `## Purpose` for individual users after the archive merges the deltas, because a delta
cannot change Purpose. `invitations` and `organization-members` are retired.

Alternative: move FR-1…FR-3 into a new folder `registration` — numbers would move between
capabilities, which the archive cannot do; a later rename is a docs-only change.

### Modules

- `invitations` is deleted with its router, emails and table.
- `accounts` keeps registration and the user repository; the members router and service go away;
  `register_organization` becomes `register`.
- `auth` drops `organization_id` from sessions and tokens and the administrator dependency.
- `app/platform/auth_context.py` holds `user_id` only; `Role` is deleted.
- `OrganizationName` and its field message are deleted from `app/platform`.

### Rollback

`downgrade` recreates the dropped tables and columns. It creates one organization per user, named
after the user, makes every user its administrator and active, and fills `organization_id` of sessions
and tokens from their user. Invitations do not come back. Code of task 0.2 runs on the result.

## Risks / Trade-offs

- [A dropped column still read somewhere] → pyright strict and the regenerated SPA client fail on any
  leftover; `test_migrations.py` runs upgrade and downgrade on data of task 0.2.
- [A user who was deactivated for a reason signs in again] → only dev databases exist; accepted by the
  user.
- [Old sessions issued with an organization] → the session rows stay valid; nothing in them depends on
  the organization after the migration.

## Interface

The public contract for tests and code. All paths are under `/api/v1`. Every state-changing request
needs a matching `Origin`. «Signed in» means the `vc_session` cookie.

### Schemas

- `Me`: `{user_id: uuid, name: str, email: str}` — no `role`, no `organization`.
- `RegistrationRequest`: `{name, email, password}`; any other field, `organization_name` included, is
  refused with 422 `validation_failed`.
- `Error`: `{error: {code: str, message: str, fields?: {[field]: str}}}`

### Routes

| Route | Who | Body | Success | Errors |
|---|---|---|---|---|
| `POST /auth/registrations` | anyone | `{name, email, password}` | 201 `{email, email_sent: bool}` | 409 `email_taken`, 422 `validation_failed` |
| `POST /auth/email-confirmations` | anyone | `{token}` | 200 `Me`, sets the cookie | 400 `invalid_link` |
| `POST /auth/sessions` | anyone | `{email, password}` | 200 `Me`, sets the cookie | 401 `invalid_credentials`, 403 `email_not_confirmed`, 429 `sign_in_locked`, 422 `validation_failed` |
| `DELETE /auth/sessions/current` | signed in | — | 204, clears the cookie | 401 `not_signed_in` |
| `GET /auth/me` | signed in | — | 200 `Me` | 401 `not_signed_in` |
| `POST /auth/password-resets` | anyone | `{email}` | 202 | 422 `validation_failed` |
| `POST /auth/password-resets/complete` | anyone | `{token, password}` | 204 | 400 `invalid_link`, 422 `validation_failed` |

Removed: every `/invitations` and `/members` route — they answer 404 like any unknown path. Removed
error codes: `account_disabled`, `invalid_invitation`, `invitation_exists`, `invitation_not_open`,
`cannot_deactivate_self`, `last_administrator`, `member_inactive`.

### Auth context

`AuthContext`: `{user_id: UUID}` — taken from the session; `Role` and `organization_id` are gone.
`require_administrator` is deleted.

### Schema after the migration

- `users`: `id, email (unique), name, password_hash, confirmed_at, created_at`.
- `sessions`, `user_tokens`: as before without `organization_id`.
- `organizations` and `invitations` do not exist.

### SPA

- «Регистрация»: fields «Имя», «Email», «Пароль»; the field message «Укажите название организации» is
  gone.
- Start page: the user's name and «Выйти»; no organization, no «Участники».
- `/members` and `/invitation` show «Страница не найдена».
- Error messages and validation texts not listed as removed stay exactly as in task 0.2.
