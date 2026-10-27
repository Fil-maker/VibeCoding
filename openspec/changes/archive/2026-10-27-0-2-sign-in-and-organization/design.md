# Design

## Context

The skeleton (task 0.1) has one module, `health`, an empty Alembic baseline `0001`, no tables, no auth
and no SPA routing. The rules already expect an auth context: `.claude/rules/data-access.md` says the
scope comes from it and every query filters by `organization_id`;
`.claude/rules/server-architecture.md` lists the auth context in `platform/`. This change creates the
first tables, the first state-changing routes and the first outgoing network calls (SMTP). Motivation:
see proposal.md «Why». Requirements: FR-1…FR-20 in the delta specs.

## Goals / Non-Goals

**Goals:**

- One auth context per request: the user id, the organization id, the role. Every later module takes
  its organization and owner scope from it.
- The first state-changing API with structured errors, a cross-site guard and single-use emailed links.
- A mail sender behind a protocol: SMTP in dev and prod, a fake in tests.

**Non-Goals:**

- A background worker or a job queue. Emails are sent right after the commit inside the request (see
  «Email delivery»).
- Rate limits by IP or per route beyond the per-email sign-in lock (FR-5).
- HTML emails. Service emails are plain text.

## Decisions

### Modules

| Module | Owns | Public surface |
|---|---|---|
| `accounts` | organizations, users; registration, confirmation, members, roles | `service.py`; `get_user_for_session` used by `auth` |
| `auth` | sessions, emailed one-time tokens, sign-in failures; sign-in, sign-out, password reset | `service.py`; `dependencies.py`: `current_user`, `current_admin` |
| `invitations` | invitations; invite, resend, revoke, preview, accept | `service.py` |

`platform/` gains `auth_context.py` (the `AuthContext` type, no queries), `passwords.py`
(the hasher), `mail.py` (the sender protocol, SMTP and fake implementations), `errors.py` (the
structured error and its handlers) and `origin.py` (the cross-site guard).

- The session-to-user dependency lives in `auth/dependencies.py`, not in `platform/`. Resolving a
  session needs `auth`'s table, and the platform never imports modules. Other modules' routers import
  `current_user` and `current_admin` from there. These dependencies are `auth`'s public entry point, like
  its `service.py`. Alternative: a placeholder dependency in the platform that `main.py` overrides.
  Rejected: an indirection with no gain, and a forgotten override fails open.
- `accounts` and `invitations` are separate because invitations carry their own lifecycle and delivery
  state. Accepting an invitation creates the user through `accounts.service`.

### Sessions (user decision)

A random 32-byte token sits in the cookie `vc_session`: HttpOnly, SameSite=Lax, Path=/, `Secure` from
the setting `SESSION_COOKIE_SECURE` (false in dev). The `sessions` table keeps only its SHA-256 hash.
Each request reads the session with its user. A session counts only when it has not expired and its
user is confirmed and active. The role is read from the user row, so a role change applies to the next
request (FR-15). Deactivation (FR-14) and a password reset (FR-8) delete the user's session rows.
Alternative: a stateless JWT. Rejected by the user: deactivation would wait for the token to expire.

### Cross-site guard

Same origin: Vite proxies `/api` in dev, and the backend serves behind the same host in prod. A
middleware refuses every `POST`/`PUT`/`PATCH`/`DELETE` under `/api/` whose `Origin` header does not
match the origin of `APP_BASE_URL`. A missing header is refused too. The answer is 403 `forbidden_origin`
(FR-20). SameSite=Lax already blocks cross-site `POST`s with cookies; the Origin check covers old
browsers and same-site subdomains. Alternative: a CSRF token in a header. Rejected: an extra round
trip and state, for no gain on a same-origin SPA.

### Passwords (user decision)

Argon2id through `argon2-cffi` with its default parameters, which hash in about 50 ms. Hashing runs in
a worker thread (`anyio.to_thread.run_sync`), so the event loop is not blocked. The hasher is verified
against a fixed dummy hash for an unknown email, so the answer takes the same time (FR-4). The hasher
reports when a stored hash needs a rehash, and a successful sign-in then rehashes the password.
Alternative: `hashlib.scrypt`. Rejected by the user.

### Emailed one-time links

Confirmation (24 h), password reset (1 h) and invitation (7 days) links carry a random 32-byte token in
the URL fragment: `{APP_BASE_URL}/confirm-email#token=…`, `/reset-password#token=…`,
`/invitation#token=…`. Browsers do not send the fragment to servers or in `Referer`, so the token
stays out of access logs. The SPA reads it and posts it in a request body. Only SHA-256 hashes are
stored. Confirmation and reset tokens live in `user_tokens` with a `purpose`. A new token of the same
purpose deletes the user's earlier ones (FR-3, FR-7). Using a token deletes it, so it is single-use. An
invitation keeps its token hash on its own row, and a resend replaces it (FR-10).

### Email delivery

The data-access rule forbids network calls inside a transaction. The service commits first, then calls
`MailSender.send` outside the transaction.

- **Invitations:** the row is the outbox. `delivery` is `pending`, then `sent` or `failed`, written in a
  second short transaction after the send. «Не отправлено» covers `pending` and `failed`. Resend
  repeats the send (FR-10).
- **Confirmation:** a failure is reported to the page (FR-1, `email_sent: false`). The unconfirmed
  registration does not block a repeat (FR-3).
- **Password reset:** a failure is logged with the user id, never the address. The page shows the common
  answer, so the result never reveals whether the email exists (FR-7).

`SmtpMailSender` uses `aiosmtplib` with a 10-second timeout; `FakeMailSender` records messages and can be
told to fail. The sender comes from a dependency factory, a lazy singleton. Alternative: an outbox
table with a worker. Deferred until a background worker exists for mail reading.

### Sign-in lock

The table `sign_in_failures` holds the normalized email and the time of each failure. Sign-in counts the
failures for that email in the last 15 minutes. With 5 or more, it refuses with 429 `sign_in_locked`
until 15 minutes after the fifth failure (FR-5). A refused attempt during a lock is not recorded, so the
lock does not extend itself. A success or a completed reset deletes the email's rows. Rows older than
the window are deleted on each sign-in for that email. The table has no `organization_id`: the email
is global and may be unknown. This is the documented exception to the database rule. The clock is
injected. Alternative: Redis. Rejected by the user: a new service for one counter.

### Concurrency

- **Unique email:** `users.email` is unique and stored normalized (trimmed, lower-cased). A race
  between two registrations ends with one unique-violation, answered 409 `email_taken`.
- **Repeated unconfirmed registration (FR-3):** in one transaction, delete the unconfirmed user's
  organization (cascade), then insert the new one.
- **Last administrator (FR-16):** role changes and deactivations lock the organization row
  (`with_for_update`). They count the active administrators under the lock. Two administrators acting
  at once are serialized.
- **One open invitation per email (FR-9):** invite locks the organization row, then checks for an open
  invitation. «Open» depends on the clock, so a partial unique index cannot express it.

### Data model (revision `0002`)

| Table | Columns |
|---|---|
| `organizations` | `id`, `name`, `created_at` |
| `users` | `id`, `organization_id`, `email` (unique), `name`, `password_hash`, `role` (`administrator`/`employee`), `is_active`, `confirmed_at` (null until confirmed), `created_at` |
| `sessions` | `id`, `organization_id`, `user_id`, `token_hash` (unique), `created_at`, `expires_at` |
| `user_tokens` | `id`, `organization_id`, `user_id`, `purpose` (`confirm_email`/`reset_password`), `token_hash` (unique), `created_at`, `expires_at` |
| `sign_in_failures` | `id`, `email`, `occurred_at`; index on (`email`, `occurred_at`) |
| `invitations` | `id`, `organization_id`, `email`, `invited_by_user_id`, `token_hash` (unique), `delivery` (`pending`/`sent`/`failed`), `sent_at`, `expires_at`, `accepted_at`, `accepted_user_id`, `revoked_at`, `created_at`; index on (`organization_id`, `created_at`) |

Every foreign key cascades from `organizations`. Deleting an organization is not offered yet. No user
row is ever deleted, except an unconfirmed registration replaced by FR-3. Deactivation only sets
`is_active`, so history survives. «Members» (FR-13) are users with `confirmed_at` set.

### Errors and validation

Every error answers `{"error": {"code": "...", "message": "<Russian>"}}`. Validation errors add
`"fields": {"<field>": "<Russian>"}`. The handler maps FastAPI's 422 to `validation_failed` with the
Russian per-field messages of FR-1, FR-8 and FR-12. Request models use `extra="forbid"`, so a body naming
`organization_id` is refused (FR-18). Text fields have the length limits of the specs. An email is
checked for one «@» with text on both sides, at most 254 characters.

### SPA routing (needs approval: a new runtime dependency)

`react-router` 7 in declarative mode (`BrowserRouter`, `Routes`). One `AuthProvider` reads `GET
/api/v1/auth/me` through TanStack Query. One `RequireUser` / `RequireAdmin` guard sends a signed-out
visitor to `/sign-in?next=<path>` and shows «Страница не найдена» to an employee on an administrator
page. Alternative: a hand-written router over the History API. Rejected: about 100 lines to maintain
for links, guards and `next`, and the next tasks add pages.

### Dev mail catcher (user decision)

A `mailpit` service in `docker-compose.yml` with a pinned image tag. SMTP is on port 1025 inside the
network, the web UI on host port 8025. The backend container's `SMTP_HOST=mailpit`. Tests never touch
SMTP; they use `FakeMailSender` through `dependency_overrides`.

### Settings

New fields in `backend/app/platform/settings.py`, each with a line in `.env.example` and a row in
`docs/tech.md`:

- `APP_BASE_URL` (required; dev `http://localhost:5173`) — links and the Origin check
- `MAIL_FROM` (required)
- `SMTP_HOST` (required), `SMTP_PORT` (default 1025), `SMTP_USERNAME` and `SMTP_PASSWORD` (optional),
  `SMTP_STARTTLS` (default false)
- `SESSION_COOKIE_SECURE` (default false)
- `SESSION_LIFETIME_DAYS=14`, `CONFIRMATION_LINK_HOURS=24`, `PASSWORD_RESET_LINK_MINUTES=60`,
  `INVITATION_LIFETIME_DAYS=7`
- `SIGN_IN_MAX_FAILURES=5`, `SIGN_IN_FAILURE_WINDOW_MINUTES=15`, `SIGN_IN_LOCK_MINUTES=15`

## Interface

The public contract for tests and code. All paths are under `/api/v1`. Every state-changing request
needs a matching `Origin`. «Signed in» means the `vc_session` cookie.

### Schemas

- `Me`: `{user_id: uuid, name: str, email: str, role: "administrator" | "employee", organization: {id: uuid, name: str}}`
- `Member`: `{id: uuid, name: str, email: str, role: "administrator" | "employee", is_active: bool}`
- `Invitation`: `{id: uuid, email: str, sent_at: datetime | null, expires_at: datetime, status: "sent" | "not_sent" | "accepted" | "revoked" | "expired"}`
- `Page[T]`: `{items: T[], next_cursor: str | null}`; query `limit` (1–100, default 50), `cursor`
- `Error`: `{error: {code: str, message: str, fields?: {[field]: str}}}`

### Routes

| Route | Who | Body | Success | Errors |
|---|---|---|---|---|
| `POST /auth/registrations` | anyone | `{organization_name, name, email, password}` | 201 `{email, email_sent: bool}` | 409 `email_taken`, 422 `validation_failed` |
| `POST /auth/email-confirmations` | anyone | `{token}` | 200 `Me`, sets the cookie | 400 `invalid_link` |
| `POST /auth/sessions` | anyone | `{email, password}` | 200 `Me`, sets the cookie | 401 `invalid_credentials`, 403 `email_not_confirmed`, 403 `account_disabled`, 429 `sign_in_locked`, 422 `validation_failed` |
| `DELETE /auth/sessions/current` | signed in | — | 204, clears the cookie | 401 `not_signed_in` |
| `GET /auth/me` | signed in | — | 200 `Me` | 401 `not_signed_in` |
| `POST /auth/password-resets` | anyone | `{email}` | 202 | 422 `validation_failed` |
| `POST /auth/password-resets/complete` | anyone | `{token, password}` | 204 | 400 `invalid_link`, 422 `validation_failed` |
| `GET /invitations` | administrator | — | 200 `Page[Invitation]`, newest first | 401, 404 `not_found` |
| `POST /invitations` | administrator | `{email}` | 201 `Invitation` (`not_sent` when mail failed) | 409 `email_taken`, 409 `invitation_exists`, 422 |
| `POST /invitations/{id}/resend` | administrator | — | 200 `Invitation` | 404 `not_found`, 409 `invitation_not_open` |
| `POST /invitations/{id}/revoke` | administrator | — | 200 `Invitation` (unchanged when not open) | 404 `not_found` |
| `POST /invitations/preview` | anyone | `{token}` | 200 `{organization_name, email}` | 400 `invalid_invitation` |
| `POST /invitations/accept` | anyone | `{token, name, password}` | 200 `Me`, sets the cookie | 400 `invalid_invitation`, 409 `email_taken`, 422 |
| `GET /members` | administrator | — | 200 `Page[Member]`, by name | 401, 404 `not_found` |
| `POST /members/{id}/deactivate` | administrator | — | 200 `Member` | 404, 409 `cannot_deactivate_self`, 409 `last_administrator` |
| `POST /members/{id}/reactivate` | administrator | — | 200 `Member` | 404 |
| `PUT /members/{id}/role` | administrator | `{role}` | 200 `Member` | 404, 409 `last_administrator`, 409 `member_inactive` |

Every state-changing route also answers 403 `forbidden_origin`. An employee gets 404 `not_found` on
every administrator route, and so does anyone asking for an id of another organization.

### Error messages (Russian, exact)

| Code | Message |
|---|---|
| `email_taken` | «Этот email уже зарегистрирован» |
| `invalid_link` | «Ссылка недействительна или устарела» |
| `invalid_invitation` | «Приглашение недействительно или устарело» |
| `invalid_credentials` | «Неверный email или пароль» |
| `email_not_confirmed` | «Подтвердите email: ссылка в письме, которое мы отправили» |
| `account_disabled` | «Учётная запись отключена. Обратитесь к администратору организации» |
| `sign_in_locked` | «Слишком много попыток входа. Попробуйте через 15 минут» |
| `invitation_exists` | «Приглашение на этот email уже отправлено» |
| `invitation_not_open` | «Приглашение уже принято, отозвано или истекло» |
| `cannot_deactivate_self` | «Нельзя отключить свою учётную запись» |
| `last_administrator` | «В организации должен остаться хотя бы один активный администратор» |
| `member_inactive` | «Сначала включите учётную запись участника» |
| `not_signed_in` | «Войдите в систему» |
| `not_found` | «Не найдено» |
| `forbidden_origin` | «Запрос отклонён» |
| `invalid_cursor` (400, any paged list) | «Некорректный курсор страницы» |
| `validation_failed` | «Проверьте поля формы»; fields: «Укажите название организации», «Укажите имя», «Укажите корректный email», «Пароль должен быть от 10 до 128 символов», «Укажите email и пароль» |

### SPA pages

| Path | Title | Access |
|---|---|---|
| `/register` | «Регистрация» | signed out |
| `/confirm-email` | «Подтверждение email» | anyone |
| `/sign-in` | «Вход» | signed out |
| `/forgot-password` | «Восстановление пароля» | signed out |
| `/reset-password` | «Новый пароль» | anyone |
| `/invitation` | «Приглашение» | anyone |
| `/` | the start page: name, organization, «Участники» for an administrator, «Выйти» | signed in |
| `/members` | «Участники»: members with «Отключить», «Включить», «Сделать администратором», «Сделать сотрудником»; invitations with «Пригласить», «Отправить ещё раз», «Отозвать» | administrator |
| any other | «Страница не найдена» | anyone |

The UI labels the statuses «Отправлено», «Не отправлено», «Принято», «Отозвано», «Истекло», the roles
«Администратор» and «Сотрудник», and the states «Активен» and «Отключён». Other UI texts are quoted in the
specs.

### SPA interface

- `App` in `frontend/src/App.tsx` takes an optional `queryClient` prop (default: the page's single
  client) and renders the routes inside `BrowserRouter`. Tests set the path with
  `window.history.pushState`, render `<App queryClient={…} />` with a fresh client, and stub `fetch`:
  the generated client looks `fetch` up on each call and requests `/api/v1/…` with the bodies of
  «Schemas» and «Routes».
- Each page's title is its `<h1>`. A request error shows `error.message` in an element with
  `role="alert"`; the messages of `error.fields` are shown next to their fields.
- One-time tokens are read from the URL fragment `#token=…`.
- Form fields (`<label>` texts) and buttons:

| Page | Fields | Buttons and links |
|---|---|---|
| «Регистрация» | «Название организации», «Имя», «Email», «Пароль» | «Зарегистрироваться» |
| «Вход» | «Email», «Пароль» | «Войти», link «Забыли пароль?», link «Регистрация» |
| «Восстановление пароля» | «Email» | «Отправить ссылку» |
| «Новый пароль» | «Новый пароль» | «Сохранить пароль» |
| «Приглашение» | «Имя», «Пароль» | «Принять приглашение» |
| start page | — | link «Участники» (administrator only), «Выйти» |
| «Участники» | «Email» (invite form) | «Пригласить»; per member «Отключить», «Включить», «Сделать администратором», «Сделать сотрудником»; per open invitation «Отправить ещё раз», «Отозвать» |

### Emails (plain text, Russian)

| Purpose | Subject |
|---|---|
| Confirmation | «Подтвердите регистрацию в VibeCoding» |
| Invitation | «Приглашение в {organization name} — VibeCoding» |
| Password reset | «Сброс пароля в VibeCoding» |

Each body holds the link and its lifetime.

### Platform interface

- `app.platform.settings.Settings`: the fields of «Settings» in snake case (`app_base_url`, `mail_from`,
  `smtp_host`, `smtp_port`, …); a missing `app_base_url`, `mail_from` or `smtp_host` raises
  `ValidationError` naming the field.
- `app.platform.passwords`: `async def hash_password(password: str) -> str`;
  `async def verify_password(password_hash: str | None, password: str) -> PasswordCheck`, where
  `PasswordCheck` has `ok: bool` and `needs_rehash: bool`; `None` verifies against the dummy hash and
  gives `ok=False`.
- `app.platform.mail`: `OutgoingEmail(to: str, subject: str, text: str)`; the protocol `MailSender` with
  `async def send(self, email: OutgoingEmail) -> None`, which raises `MailDeliveryError` on failure;
  `SmtpMailSender`, `FakeMailSender`, and the dependency `get_mail_sender() -> MailSender`.
- `app.platform.clock`: the dependency `get_clock() -> Clock`.
- `app.main.create_app(settings)` mounts the routes under `/api/v1`; the error shape, the 422 handler and
  the Origin check are observed through any route.

### Test seams

- `get_mail_sender` returns a `MailSender`; tests override it with `FakeMailSender`. The fake exposes
  `.sent: list[OutgoingEmail]` (`to`, `subject`, `text`) and `.fail_next(n)`.
- `get_clock` returns a `Clock`; tests override it with a settable clock.
- Links in emails match `{APP_BASE_URL}/<path>#token=<token>`, so tests take the token from the text.

## Risks / Trade-offs

- **Email sent after commit, inside the request.** A crash between commit and send leaves an
  invitation «Не отправлено». The administrator sees it and resends it. A confirmation can be repeated
  by registering again. Accepted until a worker exists.
- **SMTP latency** adds up to 10 s to invite and registration requests when the server hangs. Mitigation:
  the timeout, and the UI shows a pending state.
- **Argon2 CPU cost** under a burst of sign-ins. The lock limits it per email; a per-IP limit is in
  `docs/ideas.md` «Account settings».
- **Registration reveals that an email is taken** (`email_taken`). Accepted: an invitation does the same,
  and hiding it would need a second email flow. Sign-in and reset do not reveal it.
- **The Origin check refuses clients that send no `Origin`.** Only the SPA is a client; tests set the
  header.

## Migration Plan

Revision `0002` creates the six tables. No data exists before it, so nothing has to survive.
Rollback: `alembic downgrade 0001` drops the tables in reverse order. Deploy order: migrate, then start
the backend with the new env vars, which it requires at startup.

## Open Questions

None. Everything that changes the specs or the tasks was decided with the user.
