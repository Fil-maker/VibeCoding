# Personal accounts

Date: 29.10.2026 · Task: 1.1 · Change: 1-1-personal-accounts

## Goal

The concept changed on 28.10.2026 (commit `825f1e2`): VibeCoding is now a personal app, and organizations
are removed (ADR `docs/adr/0023-organizations-are-removed-anyone-can-register.md`). Task 1.1 is the first
task of stage 1 «Project trees». It only replaces organizations with personal accounts: anyone registers as
an individual user with email confirmation, invitations, members, the administrator role and the
organization filter go away, and every piece of data belongs to one user. Mailboxes, chains and projects are
later tasks.

## What was done

Design (session a23ae56f):

- The plan row 1.1 was added, the OpenSpec change `1-1-personal-accounts` was written (proposal, delta
  specs, design with «Interface», tasks) and the deltas were approved by the user.
- Deltas: FR-1 renamed «Register a user»; FR-1…FR-4, FR-6…FR-8, FR-17, FR-20 modified; FR-9…FR-16, FR-18,
  FR-19 removed; FR-21 «Users never see each other» added; the specs `invitations` and
  `organization-members` retired.
- FR-18 could not stay under the same number: the validator and the project rule forbid removing scenarios
  from a MODIFIED requirement, and both its scenarios were about organizations.

Code (session 517d4589), in vertical slices, one test then the minimal code:

- Registration takes `{name, email, password}`; a request with `organization_name` is refused with 422.
- The `invitations` module, the members routes and their schemas and error codes were removed; the 10
  former `/invitations` and `/members` routes answer 404.
- `Me` is `{user_id, name, email}`; tests for FR-21 were added (a user gets only their own profile; a
  password reset request naming another `user_id` is refused with 422).
- Migration `0003_personal_accounts.py` drops the tables `invitations` and `organizations` and the columns
  `organization_id`, `role` and `is_active`. Users keep email, password hash and confirmation; sessions and
  tokens stay with their users. Downgrade recreates one organization per user, makes the user its
  administrator and active. Six migration tests run on task 0.2 data.
- `AuthContext` holds only `user_id`; `Role`, the administrator check, the deactivation branches and
  `account_disabled` were removed; `register_organization` became `register`.
- SPA: the API client was regenerated; the form asks for name, email and password; the start page shows the
  name and «Выйти»; the «Участники» and invitation pages and `RequireAdmin` were deleted, so `/members` and
  `/invitation` show «Страница не найдена».
- Manual flow (flow-checker, stack started without `--build`): a new user registers, confirms through
  Mailpit and signs out; a formerly deactivated employee of task 0.2 signs in after the migration. All
  steps passed.
- At `/finish` the docs were updated (`architecture`, `tech`, guides, the specs were archived) and ADRs
  0035–0041 were written. The unused style `.muted` was removed from `frontend/src/components/ui.module.css`,
  and the dead setting `invitation_lifetime_days` / `INVITATION_LIFETIME_DAYS` was removed.

Test counts at the end of the code step: 21 backend unit tests, 34 SPA tests, 89 database tests.

## Key questions to the AI

- The user asked during design (answered through AskUserQuestion): what the migration does with
  organizations and users already in the database; what to do with the «active» flag when there are no
  administrators; what a person enters at registration; whether to update the glossary and the harness
  texts in this change. Answers: «Сохранить людей (рекомендую)», «Убрать флаг (рекомендую)», «Имя, email,
  пароль (рекомендую)», «Да, всё сразу (рекомендую)».
- «Одобряем дельты (включая замену FR-18 на FR-21)?» — «Да (рекомендую)».
- «Я не могу зарегистрироваться. Мне не приходит письмо на почту. Как можно это поправить?» — it was not a
  defect: registration returned `201 Created`, and in development every email goes to Mailpit
  (`SMTP_HOST: mailpit` in `docker-compose.yml`), http://localhost:8025. The first answer said real emails
  would need SMTP login and TLS support in the backend; that was wrong, because `backend/app/platform/settings.py`
  already has `smtp_username`, `smtp_password` and `smtp_starttls` (`docs/tech.md` «Environment variables»).
  Real emails need only a real SMTP server set in `.env` and `SMTP_HOST: mailpit` overridden in
  `docker-compose.yml`.
- Short confirmations in the code step: «Да, срез 1», «Убрать эти проверки», «Да, срез 2», «Да, удали»,
  «Да, Me и FR-21», «Да, деактивация», «Да, SPA», «Да, ручной поток», «Да, без --build», «Да, /finish».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Migration keeps every existing user as a personal account (same email, password, confirmation); organizations, invitations and roles are dropped; downgrade recreates one organization per user | wipe all users; keep only confirmed users | Сохранить людей | [human] |
| The is_active flag and deactivation are removed; formerly deactivated users can sign in again | keep the flag with nobody able to change it | Убрать флаг: деактивация была действием администратора, администраторов больше нет | [human] |
| Registration asks for name, email and password; the start page shows the name and «Выйти» | email and password only | Имя, email, пароль | [human] |
| This change also removes Organization, Employee, Administrator, Member and Invitation from the glossary and rewrites the harness rules, harness.md, invariant-reviewer, explore and delta-rules for a single-user owner | glossary only, harness texts in a separate minor change | Да, всё сразу | [human] |
| Delta specs of 1-1-personal-accounts approved: FR-1 renamed «Register a user», FR-1…FR-4, FR-6…FR-8, FR-17, FR-20 modified; FR-9…FR-16, FR-18, FR-19 removed; FR-21 «Users never see each other» added; invitations and organization-members retired | keep FR-18 with rewritten scenarios under old names | Да — одобрено пользователем; FR-18 заменён на FR-21, потому что его сценарии про организации нельзя убрать из MODIFIED | [human] |
| The deactivation slice merges into the migration 0003 slice: a deactivated user of task 0.2 signs in after the upgrade is the red test for removing is_active, roles and organizations | - | With the members routes gone, deactivation is observable only through the migration | [AI → accepted] |
| Migration 0003 drops users.role, users.is_active and the organization_id columns in the same migration whose models stop writing them, an exception to the database rule against dropping a column with data in the same migration that stops writing it | - | Only dev databases exist, the user decided that existing users become individual accounts (design), and downgrade restores the columns | [AI → accepted] |

ADRs written: 0035–0041.

## Mistakes and lessons

- **The brief kept FR-18; the validator did not allow it.** The brief said to change FR-18, but both of its
  scenarios were about organizations and cannot be removed from MODIFIED. It was replaced by FR-21 and the
  user approved this. Lesson: check a requirement's scenarios against the delta rules before planning to
  keep its number.
- **A replacement error in the `access-boundary` delta.** The assistant wrote that it was fixing its own
  replacement mistake and rewrote the whole file. Strict validation caught the file state before approval.
- **Tests weakened to keep the suite green.** After slice 1, 7 old tests failed on the removed
  organization name. At the user's choice («Убрать эти проверки») the asserts were dropped, which made the
  invitation tests weaker (for example, one no longer checked which organization Boris joined). It was
  acceptable only because slice 4 deleted those tests.
- **The sandbox script does not carry deletions.** It refuses to collect deleted tests, so the 7 backend and
  4 SPA test files had to be deleted by hand in the checkout after the user agreed. The `--force` workaround
  was needed once. It is listed in the handoff as a harness problem.
- **A lost harness edit.** The test move used `--ignore-other`, which only allows files outside tests and
  does not copy them; `test/appHarness.tsx` counts as such, so its edit was not carried over and the sandbox
  was already deleted. The `test-writer` redid the edit in a new sandbox. A check of the working copy
  against the sandbox before deleting it would have caught this.
- **The slice order was changed.** The `Me` slice was postponed because about 30 tests of members and
  invitations read the role and organization from `Me`; the removal of invitations went first so that the
  suite stayed green between slices.
- **A red check that proved nothing.** In the removed-routes test, 5 routes with an id passed even without
  the new code, because a missing id was already a 404. The same holds for the FR-21 reset test: it passed
  before the code and only guards against regression.
- **The preview config built the images.** `.claude/launch.json` ran `docker compose up --build`, and Docker
  could not resolve `ghcr.io`. A second configuration without `--build` was added. The first start also
  stopped by itself after about 50 seconds; the cause was not found.
- **The session's working folder drifted.** `/finish` did not start because the folder had moved to
  `openspec/changes/1-1-personal-accounts` and the skill could not find its script; the session was
  returned to the repository root and `/finish` was run again.
- **The 403 was called a leftover.** The handoff called the 403 on `/auth/registrations` a leftover of task
  0.2; the review step showed it documents the Origin guard (`OriginGuardMiddleware` answers 403
  `forbidden_origin` on every state-changing route).
- **The first email answer missed existing settings.** It said SMTP login and TLS support were missing in the
  backend, but the SMTP settings already existed.
- **The pytest warning count rose from 6 to 44.** It is one Alembic warning about the deprecated
  `path_separator`, printed on every config creation; no new kinds of warnings.

## What remains

- The «not found» answer for another user's data in FR-21 is not tested: users have no data with
  identifiers yet; the test comes with mailboxes or projects.
- The two defects of the sandbox script (no carrying of deleted tests, `--ignore-other` skips changed
  harness files), listed in the handoff.
- Nothing was committed at the time of writing.
