# Auth and accounts

Updated 27.10.2026

**Code:** `backend/app/modules/accounts/`, `backend/app/modules/auth/`, `backend/app/modules/invitations/`,
the platform files `backend/app/platform/auth_context.py`, `errors.py`, `mail.py`, `origin.py`, `pagination.py`,
`passwords.py`, `tokens.py`, `validation.py` and `clock.py`, the tests in `backend/tests/` and
`backend/tests/integration/`.

**Requirements:** [FR-1 … FR-3](../../openspec/specs/organization-registration/spec.md) registration,
[FR-4 … FR-8](../../openspec/specs/sign-in/spec.md) sign-in, sessions and password reset,
[FR-9 … FR-12](../../openspec/specs/invitations/spec.md) invitations,
[FR-13 … FR-16](../../openspec/specs/organization-members/spec.md) members,
[FR-17 … FR-20](../../openspec/specs/access-boundary/spec.md) the access boundary. The map is in
[Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Layers](../architecture.md#layers), [Data model](../architecture.md#data-model),
[Routes and API](../architecture.md#routes-and-api), [Security](../architecture.md#security).

**Related:** [Backend](backend.md), [Frontend](frontend.md).

## Modules and their files

| Module | What it does | Router |
|---|---|---|
| `accounts` | Registration of an organization, email confirmation of the registrant, the members of an organization | `router` (`/api/v1/auth`, registration) and `members_router` (`/api/v1/members`) in `backend/app/modules/accounts/router.py` |
| `auth` | Sign-in and its lock, sessions, sign-out, `GET /auth/me`, password reset, the `current_user` and `current_admin` dependencies | `router` (`/api/v1/auth`) in `backend/app/modules/auth/router.py` |
| `invitations` | Invite, list, resend, revoke, preview and accept an invitation | `router` (`/api/v1/invitations`) in `backend/app/modules/invitations/router.py` |

Each module follows the layers of [Layers](../architecture.md#layers): `router.py` → `service.py` → `domain.py`
and `repository.py` → `models.py`. Errors of the module are in `errors.py`, the texts of its service emails in
`emails.py`, its request and response models in `schemas.py`. The router takes a session-bound service class from
`service.py` (`AccountsService`, `AuthService`, `InvitationsService`) through its `get_<module>_service` factory, so no
router holds a session. `backend/app/modules/auth/dependencies.py` holds the two dependencies other modules use to
learn the caller. A module uses another module through its `service.py`, its `repository.py`, and its public
`dependencies.py`, `schemas.py` or `errors.py`; it never imports the other module's models or private functions.
For example, the accounts service ends sessions and issues confirmation tokens through the auth service, the
invitations service uses the accounts repository and service and raises `EmailTaken` from `backend/app/modules/accounts/errors.py`,
the invitations router takes `Me` from `backend/app/modules/auth/schemas.py`, and the auth service reads users through the accounts
repository.

The platform files do the following:

- `auth_context.py`: `AuthContext` (user id, organization id, role) and `Role`. Every query takes its scope from it.
- `tokens.py`: `new_token()` makes a random URL-safe value of 32 bytes; `hash_token()` gives the SHA-256 hex digest
  that is stored instead.
- `passwords.py`: `hash_password` and `verify_password` run Argon2id in a worker thread. An unknown email is checked
  against a dummy hash, and `needs_rehash` tells the service to store a fresh hash.
- `mail.py`: the `MailSender` protocol, `SmtpMailSender` (aiosmtplib with a timeout), `FakeMailSender` for tests,
  the `get_mail_sender` dependency and `build_link`.
- `origin.py`: `OriginGuardMiddleware`, see [Access boundary](#access-boundary).
- `errors.py`: `HttpError`, `NotFound`, `error_responses`, `register_domain_errors`, `register_error_handlers`,
  see [Errors over HTTP](#errors-over-http).
- `validation.py`: `RequestModel` (unknown fields are refused) and the shared field types with Russian messages.
- `pagination.py`: `Page[T]` and the page limits.
- `clock.py`: `Clock`, `SystemClock` and `get_clock`, see [Emails and time in tests](#emails-and-time-in-tests).

## Registration and email confirmation

1. `POST /api/v1/auth/registrations` (anyone) calls `backend/app/modules/accounts/service.py` `register_organization`. In one
   transaction it looks up the email across the installation (FR-1). A confirmed user of the email answers
   `email_taken` 409. An unconfirmed registration of the same email is replaced: its organization is deleted with
   its users and tokens (FR-3). The new organization and its unconfirmed administrator are stored, with a
   confirmation token that replaces earlier tokens of the same purpose. The token lives for
   `CONFIRMATION_LINK_HOURS`.
2. After the commit the confirmation email goes out with the link `<APP_BASE_URL>/confirm-email#token=…`. When the
   send fails, the answer is still 201, with `email_sent: false`; the account stays unconfirmed and a repeated
   registration replaces it. A failed send is logged and not raised.
3. The SPA sends the token from the link to `POST /api/v1/auth/email-confirmations`. One `DELETE … RETURNING`
   consumes the token, so the link works once. The user gets `confirmed_at`, a session starts, and the answer is
   `Me` with the `vc_session` cookie. An unknown, used or expired token answers 400 `invalid_link`.

The rules are in [FR-1](../../openspec/specs/organization-registration/spec.md), [FR-2](../../openspec/specs/organization-registration/spec.md)
and [FR-3](../../openspec/specs/organization-registration/spec.md). The decision that the email is confirmed before
the first sign-in is in [ADR 0009](../adr/0009-the-registrant-s-email-is-confirmed.md).

## Sign-in, the lock and sessions

`POST /api/v1/auth/sessions` calls `backend/app/modules/auth/service.py` `sign_in`. The decision is made in `_attempt_sign_in`, in one
transaction, in this order:

1. Failures of the email older than the counting window plus the lock are deleted.
2. If the failures lock the email, the answer is 429 `sign_in_locked`. The lock is checked before the password, so
   a correct password is refused while the lock holds. The rule is `is_locked` in `backend/app/modules/auth/domain.py`: 5 failures within
   15 minutes lock sign-in for 15 minutes from the last failure. Refused attempts are not recorded, so the lock does
   not extend itself.
3. The password is checked. A wrong password and an unknown email both record a failure and answer 401
   `invalid_credentials`.
4. A correct password of a user who has not confirmed the email answers 403 `email_not_confirmed`; a correct
   password of a deactivated user answers 403 `account_disabled`. Neither records a failure.
5. A success clears the failures of the email, stores a fresh hash when `needs_rehash` is set, and starts a session.

The refusals are returned from the transaction and raised afterwards, so a recorded failure is committed even though
the call answers with an error. The failures are in the `sign_in_failures` table, which has no organization column,
because the email may be unknown ([Data model](../architecture.md#data-model)).

**Sessions.** `start_session` stores a row in `sessions` with the SHA-256 of a random token and an expiry of
`SESSION_LIFETIME_DAYS` from now. The browser gets the raw token in the `vc_session` cookie: `HttpOnly`,
`SameSite=Lax`, `Path=/`, `Max-Age` equal to the lifetime, and `Secure` as set by `SESSION_COOKIE_SECURE`
(`set_session_cookie` in `backend/app/modules/auth/dependencies.py`). Every request resolves the cookie in `current_user`: the session
must be live, and the user must be confirmed and active. The role and the active flag are read from the database on
each request. Otherwise the answer is 401 `not_signed_in`.

- `DELETE /api/v1/auth/sessions/current` ends this browser's session only and deletes the cookie.
- `GET /api/v1/auth/me` answers the signed-in user as `Me`.
- Deactivating a member and completing a password reset delete all of the user's sessions. Reactivating a member does
  not restore them: the user signs in again.

The rules are in [FR-4](../../openspec/specs/sign-in/spec.md), [FR-5](../../openspec/specs/sign-in/spec.md) and
[FR-6](../../openspec/specs/sign-in/spec.md). The storage of sessions in PostgreSQL is in
[ADR 0012](../adr/0012-sessions-are-stored-server-side-in.md); the lock defaults are in
[ADR 0014](../adr/0014-defaults-invitation-7-days-email-confirmation.md).

## Password reset

- `POST /api/v1/auth/password-resets` takes an email and always answers 202 with no body. Only a confirmed user
  gets a reset token, which replaces the earlier reset tokens and lives for `PASSWORD_RESET_LINK_MINUTES`. The
  email with the link `<APP_BASE_URL>/reset-password#token=…` goes out after the commit; a failed send is logged only.
- `POST /api/v1/auth/password-resets/complete` takes the token and the new password and answers 204. In one
  transaction it consumes the token (an unknown, used or expired token answers 400 `invalid_link`), stores the new
  Argon2id hash, deletes all sessions of the user and clears the sign-in failures of the email.

The route does not check the active flag. A deactivated user can set a new password, but sign-in still refuses them
with `account_disabled`. The rules are in [FR-7](../../openspec/specs/sign-in/spec.md) and
[FR-8](../../openspec/specs/sign-in/spec.md).

## Invitations

**Invite.** `POST /api/v1/invitations` (administrator) calls `backend/app/modules/invitations/service.py` `invite`. In one transaction:

- it locks the organization row (`SELECT … FOR UPDATE`), which serializes the invitations of the organization;
- a confirmed user of the email answers `email_taken` 409;
- an open invitation of the organization for the email answers `invitation_exists` 409;
- otherwise a pending invitation is stored with the hash of its token and an expiry of `INVITATION_LIFETIME_DAYS`.

An unconfirmed registration of the email does not block the invitation. Accepting the invitation replaces that
registration, as a repeated registration does.

After the commit `_deliver` sends the link `<APP_BASE_URL>/invitation#token=…` outside any transaction. The outcome is
written in a second transaction into the `delivery` column, `sent` with `sent_at`, or `failed`. The write only
applies while the stored token hash is still the one that was sent, so a resend that ran meanwhile is not overwritten.
The answer is 201 with the `Invitation`; its `status` is `sent`, or `not_sent` when the mail failed. The status rules
are in [Data model](../architecture.md#data-model).

**Resend.** `POST /api/v1/invitations/{invitation_id}/resend` locks the invitation row. A link that is not open
answers `invitation_not_open` 409. An open one gets a new token, which makes the old link stop working, a new expiry
and `pending` delivery, and then it is sent again as in invite.

**Revoke.** `POST /api/v1/invitations/{invitation_id}/revoke` sets `revoked_at` on an open invitation. An invitation
that is not open is returned unchanged, with no error.

**List.** `GET /api/v1/invitations` returns the organization's invitations newest first, in pages.

**Preview.** `POST /api/v1/invitations/preview` (anyone, with the token) returns the organization name and the email
of an open invitation. Otherwise it answers 400 `invalid_invitation`. It changes nothing.

**Accept.** `POST /api/v1/invitations/accept` (anyone, with the token, a name and a password) hashes the password
before the transaction. Inside it, the invitation row is locked with `FOR UPDATE`, and a link that is not open answers
`invalid_invitation`. Then `backend/app/modules/accounts/service.py` `join_organization_as_employee` creates a confirmed, active employee
with the invitation's email; a confirmed user of that email answers `email_taken` 409, and so does a unique violation
at commit. The invitation gets `accepted_at` and `accepted_user_id`, a session starts, and the answer is `Me` with the
`vc_session` cookie. A second acceptance of the same link waits for the lock and then answers `invalid_invitation`.

The rules are in [FR-9 … FR-12](../../openspec/specs/invitations/spec.md). The lifetimes are the defaults of
[ADR 0014](../adr/0014-defaults-invitation-7-days-email-confirmation.md).

## Members and the last administrator

- `GET /api/v1/members` (administrator) lists the confirmed members of the caller's organization, ordered by name and
  id, in pages.
- `POST /api/v1/members/{member_id}/deactivate`, `POST …/reactivate` and `PUT …/role` (administrator) each run
  `_lock_and_find` in `backend/app/modules/accounts/service.py`. It locks the organization row first, then finds the member among the
  confirmed members of the caller's organization, or answers 404 `not_found`.

The rules run after that lookup:

- **Deactivate.** Your own account answers `cannot_deactivate_self` 409, checked first. Deactivating the last active
  administrator answers `last_administrator` 409. Otherwise the member becomes inactive and all of their sessions are
  deleted.
- **Reactivate.** The member becomes active again; no session is restored.
- **Role.** Making an inactive member an administrator answers `member_inactive` 409. Demoting the last active
  administrator answers `last_administrator` 409. The role applies to the next request, because it is read from the
  database each time.

The lock makes two administrators who remove each other serialize. The second change sees the first one: it answers
`last_administrator`, or 404 `not_found` when the first change already removed the second change's author from the
administrator role ([ADR 0018](../adr/0018-fr-16-two-administrators-remove-each.md)). The rules are in
[FR-13 … FR-16](../../openspec/specs/organization-members/spec.md); the scope of this task is in
[ADR 0010](../adr/0010-in-this-task-the-administrator-lists.md) and the self-deactivation order is in
[ADR 0019](../adr/0019-when-the-only-administrator-deactivates-themselves.md).

## Access boundary

- **Signed out.** A route that needs a session answers 401 `not_signed_in`. The dependency is `current_user`.
- **Employee on an administrator route.** `current_admin` raises `NotFound`, so the answer is 404 `not_found` with
  «Не найдено», the same as for a missing page.
- **Organization filter.** Every query of an administrator takes its `organization_id` from `AuthContext`, never
  from the request. A record of another organization is not found by its id, so it answers 404 like a missing one.
  The anonymous invitation links (preview, accept) are the exception: they look the invitation up by the hash of
  its token alone (`get_by_token_hash` in `backend/app/modules/invitations/repository.py`), because the link is the
  only key the caller has.
- **Unknown fields.** Request bodies extend `RequestModel`, which refuses unknown fields. A body that carries an
  `organization_id` answers 422 `validation_failed`.
- **Origin.** `OriginGuardMiddleware` runs before the routes. A POST, PUT, PATCH or DELETE to `/api/` must carry an
  `Origin` equal to the origin of `APP_BASE_URL`. A missing or foreign origin answers 403 `forbidden_origin`.

The rules are in [FR-17 … FR-20](../../openspec/specs/access-boundary/spec.md) and in
[Security](../architecture.md#security).

## Errors over HTTP

Domain errors carry no HTTP status. Each router declares `ERROR_MAPPING: dict[type[Exception], HttpError]`:
`backend/app/modules/accounts/router.py`, `backend/app/modules/auth/router.py` and `backend/app/modules/invitations/router.py`. `main.py` passes each mapping to
`register_domain_errors`, which installs one handler per error class. A mapping may answer an error of another module:
`EmailTaken` is raised by the invitations service and answered by the accounts mapping.

`register_error_handlers` installs the handlers that every route shares:

- `NotFound` answers 404 `not_found` with the message «Не найдено»;
- a request validation error answers 422 `validation_failed` with `fields`, the message per field. A field validator
  in `validation.py` names its Russian text; a missing or wrong-typed field takes the text of `FIELD_MESSAGES` in
  `errors.py`;
- another framework HTTP error keeps FastAPI's `{"detail"}` shape.

The shape of every answer is in [Routes and API](../architecture.md#routes-and-api).

## Adding an administrator-only route

The members routes in `backend/app/modules/accounts/router.py` are the pattern.

1. Declare the dependencies in the module's `router.py`:
   `Admin = Annotated[AuthContext, Depends(current_admin)]` and
   `Service = Annotated[AccountsService, Depends(get_accounts_service)]` (the module's own service class and factory,
   as `backend/app/modules/invitations/router.py` does with `InvitationsService`). Take the caller as `context: Admin` and the service as
   `service: Service`. The router holds no session.
2. Parse the input into a `RequestModel` subclass in `schemas.py`, so unknown fields are refused.
3. Write the use case as a function in `service.py` that opens `async with session.begin()` and passes
   `context.organization_id` to every repository call, and add a method to the service class that delegates to it.
   When the decision counts members, lock the organization row first, as `_lock_and_find` does.
4. In `repository.py`, every query filters by `organization_id` and takes it as a parameter. Never build SQL from strings.
5. Raise a domain error from `errors.py` for an expected failure, add it to the module's `ERROR_MAPPING`, and list
   every status the route answers in `responses=error_responses(…)`, including 401 and 404.
6. For a new module, add its `ERROR_MAPPING` to `main.py` with `register_domain_errors`, and include its router there.
7. Update the route in [Routes and API](../architecture.md#routes-and-api) and run `just api-client`, so the SPA's
   generated client follows the new route.
8. Test it through HTTP. Add the route to `ADMIN_ROUTES` in `backend/tests/integration/test_access_boundary.py`.
   The employee and signed-out checks run on every entry of that list. The other-organization check runs on the
   entries with an `{id}` in the path; the collection routes are covered by the separate list test.

## Emails and time in tests

- `backend/tests/integration/conftest.py` builds the `app` fixture with `create_app(settings_for(...))` from
  `backend/tests/factories.py`, and overrides two dependencies: `get_mail_sender` returns the `mail` fixture, a
  `FakeMailSender`, and `get_clock` returns the `clock` fixture, a `SettableClock` in `backend/tests/settable_clock.py`.
- `FakeMailSender.sent` holds the emails in the order they were sent. `fail_next(n)` makes the next `n` sends raise
  `MailDeliveryError`. `token_from(email)` reads the token from the link in the body.
- `SettableClock` starts at `CLOCK_START` (2099-01-01 12:00 UTC) and moves only when a test calls `advance(delta)`.
  No test sleeps. The start is far in the future, so a cookie dated by this clock does not expire for the HTTP client.
- `Factories` builds data through the public API: `unconfirmed_admin`, `confirmed_admin`, `signed_in(account)`,
  `employee(admin)`, and `invitation(admin, status)`, where `admin` is the administrator's client. The status `not_sent` fails the next send, and
  `expired` moves the clock 8 days.
- The `client` fixture is a client without a session whose requests carry the `Origin` of `APP_BASE_URL`.
- `backend/tests/members_api.py` and `backend/tests/invitations_api.py` hold the request helpers and the exact Russian
  messages the tests compare.
- The integration tests of the accounts, auth and invitations modules go through the HTTP API, not the services.
  Public platform functions have unit tests, and the health module keeps its own unit tests, `test_service.py` and
  `test_router.py` ([ADR 0016](../adr/0016-change-0-2-tests-sit-at.md)).
