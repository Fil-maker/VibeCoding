# Auth and accounts

Updated 29.10.2026

**Code:** `backend/app/modules/accounts/`, `backend/app/modules/auth/`, the platform files
`backend/app/platform/auth_context.py`, `errors.py`, `mail.py`, `origin.py`, `passwords.py`, `tokens.py`,
`validation.py` and `clock.py`, the tests in `backend/tests/` and `backend/tests/integration/`.

**Requirements:** [FR-1 … FR-3](../../openspec/specs/organization-registration/spec.md) registration,
[FR-4 … FR-8](../../openspec/specs/sign-in/spec.md) sign-in, sessions and password reset,
[FR-17, FR-20 and FR-21](../../openspec/specs/access-boundary/spec.md) the access boundary. The map is in
[Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Layers](../architecture.md#layers), [Data model](../architecture.md#data-model),
[Routes and API](../architecture.md#routes-and-api), [Security](../architecture.md#security).

**Related:** [Backend](backend.md), [Frontend](frontend.md).

## Personal accounts

Every user is a personal account. A user registers, confirms the email, signs in and owns their data. There are
no organizations, roles, invitations, members or deactivation. The decisions are in
[ADR 0023](../adr/0023-organizations-are-removed-anyone-can-register.md) and
[ADR 0036](../adr/0036-the-is-active-flag-and-deactivation.md). The caller is identified by `AuthContext`, which
holds the `user_id` and nothing else.

## Modules and their files

| Module | What it does | Router |
|---|---|---|
| `accounts` | Registration of a user; the table `users` | `router` (`/api/v1/auth`, `POST /registrations`) in `backend/app/modules/accounts/router.py` |
| `auth` | Email confirmation, sign-in and its lock, sessions, sign-out, `GET /auth/me`, password reset, the `current_user` dependency | `router` (`/api/v1/auth`) in `backend/app/modules/auth/router.py` |

Each module follows the layers of [Layers](../architecture.md#layers): `router.py` → `service.py` and
`repository.py` → `models.py`. A module holds `domain.py` only for pure rules; `backend/app/modules/auth/domain.py` has the sign-in lock.
Errors of the module are in `errors.py`, the texts of its service emails in `emails.py`, its request and response
models in `schemas.py`. The router takes a session-bound service class from `service.py` (`AccountsService`,
`AuthService`) through its `get_<module>_service` factory, so no router holds a session.
`backend/app/modules/auth/dependencies.py` holds `current_user`, which other modules use to learn the caller.
A module uses another module through its `service.py`, its `repository.py`, and its public `dependencies.py`,
`schemas.py` or `errors.py`; it never imports the other module's models or private functions. For example, the
accounts service issues the confirmation token through the auth service, and the auth service reads users through
the accounts repository.

The API has two routers besides health: accounts and auth. A path that no route serves answers 404 `not_found`,
the same as any unknown path.

The platform files do the following:

- `auth_context.py`: `AuthContext`, which holds the caller's `user_id`. Every query of the caller's own data takes
  its scope from it.
- `tokens.py`: `new_token()` makes a random URL-safe value of 32 bytes; `hash_token()` gives the SHA-256 hex digest
  that is stored instead.
- `passwords.py`: `hash_password` and `verify_password` run Argon2id in a worker thread. An unknown email is checked
  against a dummy hash, and `needs_rehash` tells the service to store a fresh hash.
- `mail.py`: the `MailSender` protocol, `SmtpMailSender` (aiosmtplib with a timeout), `FakeMailSender` for tests,
  the `get_mail_sender` dependency and `build_link`.
- `origin.py`: `OriginGuardMiddleware`, see [Access boundary](#access-boundary).
- `errors.py`: `HttpError`, `NotFound`, `error_responses`, `register_domain_errors`, `register_error_handlers`,
  see [Errors over HTTP](#errors-over-http).
- `validation.py`: `RequestModel` (`extra="forbid"`, so an unknown field is refused) and the shared field types with
  Russian messages.
- `clock.py`: `Clock`, `SystemClock` and `get_clock`, see [Emails and time in tests](#emails-and-time-in-tests).

## Registration and email confirmation

1. `POST /api/v1/auth/registrations` (anyone) takes `RegistrationRequest`, which holds `name`, `email` and
   `password` and nothing else. Any other field, `organization_name` included, answers 422 `validation_failed`.
   The fields are checked as follows: `name` is trimmed and holds 1 to 200 characters, else «Укажите имя»; `email`
   is trimmed, lower-cased, holds a local part and a domain with no second `@`, and is at most 254 characters, else
   «Укажите корректный email»; `password` holds 10 to 128 characters, else «Пароль должен быть от 10 до 128 символов».
   The route calls `register` in `backend/app/modules/accounts/service.py`. In one transaction it looks up the email
   across the installation (FR-1). A confirmed user of the email answers `email_taken` 409. An unconfirmed user of the
   same email is replaced: the row is deleted, and its sessions and tokens go with it by the database cascade
   (FR-3). The new user is stored unconfirmed, with a confirmation token that lives for `CONFIRMATION_LINK_HOURS`.
   A unique violation at commit also answers `email_taken`.
2. After the commit the confirmation email goes out with the link `<APP_BASE_URL>/confirm-email#token=…`. The answer
   is 201 with `RegistrationResult` (`email`, `email_sent`). When the send fails, the answer is still 201, with
   `email_sent: false`; the account stays unconfirmed and a repeated registration replaces it. A failed send is
   logged and not raised.
3. The SPA sends the token from the link to `POST /api/v1/auth/email-confirmations`. One `DELETE … RETURNING`
   consumes the token, so the link works once. The user gets `confirmed_at`, a session starts, and the answer is
   `Me` with the `vc_session` cookie. An unknown, used or expired token answers 400 `invalid_link`.

The rules are in [FR-1](../../openspec/specs/organization-registration/spec.md), [FR-2](../../openspec/specs/organization-registration/spec.md)
and [FR-3](../../openspec/specs/organization-registration/spec.md). The decision that the email is confirmed before
the first sign-in is in [ADR 0009](../adr/0009-the-registrant-s-email-is-confirmed.md); the registration fields are
in [ADR 0037](../adr/0037-registration-asks-for-name-email-and.md).

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
4. A correct password of a user who has not confirmed the email answers 403 `email_not_confirmed`. It records no
   failure.
5. A success clears the failures of the email, stores a fresh hash when `needs_rehash` is set, and starts a session.
   The answer is 200 with `Me`.

The refusals are returned from the transaction and raised afterwards, so a recorded failure is committed even though
the call answers with an error. The failures are in the `sign_in_failures` table, which has no user column,
because the email may be unknown ([Data model](../architecture.md#data-model)).

**Sessions.** `start_session` stores a row in `sessions` with the SHA-256 of a random token and an expiry of
`SESSION_LIFETIME_DAYS` from now. The browser gets the raw token in the `vc_session` cookie: `HttpOnly`,
`SameSite=Lax`, `Path=/`, `Max-Age` equal to the lifetime, and `Secure` as set by `SESSION_COOKIE_SECURE`
(`set_session_cookie` in `backend/app/modules/auth/dependencies.py`). Every request resolves the cookie in `current_user`: the session
must be live, and the user must be confirmed. The confirmation is read from the database on each request.
Otherwise the answer is 401 `not_signed_in`.

- `DELETE /api/v1/auth/sessions/current` ends this browser's session only and deletes the cookie.
- `GET /api/v1/auth/me` answers the signed-in user as `Me`: `user_id`, `name` and `email`.
- Completing a password reset deletes all sessions of the user.

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

The rules are in [FR-7](../../openspec/specs/sign-in/spec.md) and [FR-8](../../openspec/specs/sign-in/spec.md).

## Access boundary

- **Signed out.** A route that needs a session answers 401 `not_signed_in`. The dependency is `current_user`.
- **Own data only.** Every query of the caller's own data takes its `user_id` from `AuthContext`, never from the
  request. `find_by_email` is the one installation-wide query, because sign-in, registration and password reset start
  without a signed-in user. No route reads another user's data: `GET /api/v1/auth/me` answers only the caller.
- **Unknown fields.** Request bodies extend `RequestModel`, which refuses unknown fields. A body with an extra field,
  such as `organization_name`, answers 422 `validation_failed`.
- **Origin.** `OriginGuardMiddleware` runs before the routes. A POST, PUT, PATCH or DELETE to `/api/` must carry an
  `Origin` equal to the origin of `APP_BASE_URL`. A missing or foreign origin answers 403 `forbidden_origin`. Every
  state-changing route declares 403 in its `responses`.

The rules are in [FR-17 … FR-21](../../openspec/specs/access-boundary/spec.md) and in
[Security](../architecture.md#security).

## Errors over HTTP

Domain errors carry no HTTP status. Each router declares `ERROR_MAPPING: dict[type[Exception], HttpError]`:
`backend/app/modules/accounts/router.py` and `backend/app/modules/auth/router.py`. `main.py` passes each mapping to
`register_domain_errors`, which installs one handler per error class.

`register_error_handlers` installs the handlers that every route shares:

- `NotFound`, and any HTTP 404 such as an unknown path, answers 404 `not_found` with the message «Не найдено»;
- a request validation error answers 422 `validation_failed` with `fields`, the message per field. A field validator
  in `validation.py` names its Russian text; a missing or wrong-typed field takes the text of `FIELD_MESSAGES` in
  `errors.py`;
- another framework HTTP error keeps FastAPI's `{"detail"}` shape.

The shape of every answer is in [Routes and API](../architecture.md#routes-and-api).

## Adding a route of the signed-in user

The `read_me` route in `backend/app/modules/auth/router.py` is the pattern.

1. Declare the caller and the service in the module's `router.py`: `context: Annotated[AuthContext, Depends(current_user)]`
   and `Service = Annotated[<Module>Service, Depends(get_<module>_service)]`. Take the caller as `context` and the service
   as `service`. The router holds no session.
2. Parse the input into a `RequestModel` subclass in `schemas.py`, so unknown fields are refused.
3. Write the use case as a function in `service.py` that opens `async with session.begin()` and passes
   `context.user_id` to every repository call that reads or writes the caller's data. Add a method to the service class
   that delegates to it.
4. In `repository.py`, take the scope as a parameter. Never build SQL from strings.
5. Raise a domain error from `errors.py` for an expected failure, add it to the module's `ERROR_MAPPING`, and list
   every status the route answers in `responses=error_responses(…)`, including 401 for a route that needs the caller,
   and 403 for a state-changing route.
6. For a new module, add its `ERROR_MAPPING` to `main.py` with `register_domain_errors`, and include its router there.
7. Update the route in [Routes and API](../architecture.md#routes-and-api) and run `just api-client`, so the SPA's
   generated client follows the new route.
8. Test it through HTTP in `backend/tests/integration/`. A signed-out request answers 401 `not_signed_in`, and the
   caller gets only their own data ([FR-21](../../openspec/specs/access-boundary/spec.md)).

## Emails and time in tests

- `backend/tests/integration/conftest.py` builds the `app` fixture with `create_app(settings_for(...))` from
  `backend/tests/factories.py`, and overrides two dependencies: `get_mail_sender` returns the `mail` fixture, a
  `FakeMailSender`, and `get_clock` returns the `clock` fixture, a `SettableClock` in `backend/tests/settable_clock.py`.
- `FakeMailSender.sent` holds the emails in the order they were sent. `fail_next(count)` makes the next `count` sends
  raise `MailDeliveryError`. The function `token_from(email)` in `factories.py` reads the token from the link in the body.
- `SettableClock` starts at `CLOCK_START` (2099-01-01 12:00 UTC) and moves only when a test calls `advance(delta)`.
  No test sleeps. The start is far in the future, so a cookie dated by this clock does not expire for the HTTP client.
- `Factories` builds data through the public API: `unconfirmed_user(...)` and `confirmed_user(...)` register a user
  and return an `Account` (`email`, `password`, `name`, `user_id`); `signed_in(account)` returns a client with a
  session; `open_client(origin)` returns a client with its own cookies. `registration_body` and `sign_in` are the
  request helpers of the same module.
- The `client` fixture is a client without a session whose requests carry the `Origin` of `APP_BASE_URL`.
- The integration tests of the accounts and auth modules go through the HTTP API, not the services.
  Public platform functions have unit tests, and the health module keeps its own unit tests, `test_service.py` and
  `test_router.py` ([ADR 0016](../adr/0016-change-0-2-tests-sit-at.md)).
