# Plan

Version 0.6 · 29.10.2026

Changes in 0.6: task 1.1 «Personal accounts» done.

Changes in 0.5: task 1.1 «Personal accounts».

Changes in 0.4: task 0.2 «Sign-in and organization» done.

Changes in 0.3: task 0.2 «Sign-in and organization».

Changes in 0.2: task 0.1 «Application skeleton» done.

Changes in 0.1: task 0.1 «Application skeleton».

## How work runs

- A task is one change: one branch, one OpenSpec change, one journal note.
- `/feature` leads a task from the plan row to `/finish`; `/fix` leads a bug.
- «Done when» is what the user will see, in checkable sentences, each ending with a period.
- FR is «—» until the spec delta is approved.
- Ids are stable: a new task takes the highest id + 1; dropped ids are not reused.

## Tasks

| # | Task | FR | Done when |
|---|---|---|---|

## Done

| # | Task | FR | Done when |
|---|---|---|---|
| 0.1 | **Application skeleton.** FastAPI backend, React SPA and PostgreSQL start together with one command; technical change, no specs (`skip_specs`) | — | `just dev` starts the database, the backend and the SPA. The SPA page shows the backend's health status, in Russian, read through the generated API client. `just check` and `just test-all` pass with the backend and frontend checks included. |
| 0.2 | **Sign-in and organization.** An organization registers itself, its registrant becomes the first administrator, employees join by an emailed invitation; sign-in with email and password, password reset by email, members management; the organization and owner filter for all later data | FR-1…FR-20 | A new organization registers on the page «Регистрация», and its registrant signs in after following the confirmation link from the email caught by Mailpit. The administrator invites an employee by email; the employee accepts the invitation, sets a password and signs in; a used, revoked or expired invitation is refused. A user who forgot the password resets it by the emailed link, and their old sessions stop working. After 5 wrong passwords in 15 minutes sign-in for that email is locked for 15 minutes. The administrator sees the members of the organization, deactivates an employee, who can no longer sign in, and appoints another administrator; the last active administrator cannot be removed. An employee cannot open the administrator's pages or actions, and a user of organization A gets «not found» for data of organization B. When SMTP fails, the invitation is shown as «not sent» and can be sent again. `just check` and `just test-all` pass. |
| 1.1 | **Personal accounts.** Organizations are removed: anyone registers as an individual user with email confirmation; invitations, members, roles, deactivation and the organization filter go away; every piece of data belongs to one user | FR-1…FR-4, FR-6…FR-8, FR-17, FR-20, FR-21; removes FR-9…FR-16, FR-18, FR-19 | A visitor registers on «Регистрация» with a name, email and password, follows the confirmation link from the email caught by Mailpit and lands on the start page with their name and «Выйти», without any organization. The pages «Участники» and invitation acceptance answer «Страница не найдена», and the invitation and members API no longer exists. Users who existed before the migration sign in with their old email and password, each as a separate account, formerly deactivated ones included. A user never gets another user's data: a session token of one user gives only their own profile. Sign-in, lock, sign-out and password reset work as before. `just check` and `just test-all` pass. |
