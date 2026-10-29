# Tasks

## 1. Scenario tests (test-writer, TDD sandbox)

- [x] 1.1 Rewrite the backend integration tests of FR-1…FR-8, FR-17, FR-20 and FR-21 against design «Interface» and delete the tests of FR-9…FR-16, FR-18 and FR-19 (`test_invitations_*.py`, `test_members.py`, `test_member_roles.py`, `invitations_api.py`, `members_api.py`) — check — the new tests fail on the current code for the right reason
- [x] 1.2 Update `backend/tests/factories.py`: `unconfirmed_user`/`confirmed_user` without an organization or role, no `employee` or `invitation` factories — check — every remaining test uses only these factories
- [x] 1.3 Add a migration test: users of task 0.2 (an administrator, an employee, a deactivated employee, an unconfirmed registrant in two organizations) survive the upgrade with the same email, password hash and confirmation, and the downgrade runs on the result — check — it fails before the new migration exists
- [x] 1.4 Rewrite the SPA tests of registration, sign-in, the start page and the guards; delete `App.members*.test.tsx`, `App.invitation.test.tsx` and `membersFixtures.tsx`; add a test that `/members` and `/invitation` show «Страница не найдена» — check — they fail on the current SPA

## 2. Backend (code-writer)

- [x] 2.1 Add migration `0003` per design «Existing users become individual accounts» and «Rollback» — check — `just test-db` migration tests pass and alembic shows no drift
- [x] 2.2 Reduce `AuthContext` to `user_id`, delete `Role` and `require_administrator`; drop `organization_id` from the `auth` models, repository and service; remove the deactivated branches and `account_disabled` — check — pyright strict passes
- [x] 2.3 Change `accounts`: registration without an organization (`register`), the `Me` schema without `role` and `organization`, delete the members router and service, `Organization` model, `OrganizationName` and its field message — check — FR-1…FR-3 tests pass
- [x] 2.4 Delete the `invitations` module and its router registration — check — `/api/v1/invitations` and `/api/v1/members` answer 404 and `just test-db` passes

## 3. SPA (code-writer)

- [x] 3.1 Regenerate the API client (`just api-client`) — check — `tsc --strict` points only at the code changed in 3.2–3.3
- [x] 3.2 Registration form without «Название организации»; start page with the name and «Выйти» only — check — the SPA tests of registration and the start page pass
- [x] 3.3 Delete the pages «Участники» and invitation acceptance, `RequireAdmin` and their routes — check — the `/members` and `/invitation` test passes and `just test` is green

## 4. Docs and harness (main session at /finish through /document)

- [x] 4.1 `docs/domain.md`: drop Organization, Employee, Administrator, Member and Invitation from the glossary; requirements map; FR-9…FR-16, FR-18, FR-19 into «Cancelled numbers»; `Last FR number: FR-21` — check — `just check` doc facts pass
- [x] 4.2 Rewrite the `## Purpose` of `organization-registration`, `sign-in` and `access-boundary` after the archive — check — no Purpose mentions an organization, administrator or employee
- [x] 4.3 `.claude/rules/data-access.md`, `database.md` and the other rules naming organizations, `.claude/harness.md`, `.claude/agents/invariant-reviewer.md`, `.claude/skills/explore/SKILL.md`, `.claude/skills/feature/SKILL.md`, `.claude/skills/feature/delta-rules.md` and `openspec/config.yaml` speak of a single-user owner — check — `grep -ri "organization\|employee\|administrator"` over them finds only history
- [x] 4.4 Implementation docs (`docs/architecture.md`, `docs/tech.md`, `docs/guide/`) through `/document` — check — doc-checkers report no mismatch

## 5. Verification

- [x] 5.1 `just check` passes — check — exit code 0
- [x] 5.2 `/test` all (unit and database) — check — all green
- [x] 5.3 Manual flow in the browser on the running stack: register, confirm through Mailpit, start page, sign out, sign in with a user who existed before the migration — check — flow-checker reports PASS for every step

## 6. Done when (plan task 1.1)

- [x] 6.1 A visitor registers on «Регистрация» with a name, email and password, follows the confirmation link from the email caught by Mailpit and lands on the start page with their name and «Выйти», without any organization.
- [x] 6.2 The pages «Участники» and invitation acceptance answer «Страница не найдена», and the invitation and members API no longer exists.
- [x] 6.3 Users who existed before the migration sign in with their old email and password, each as a separate account, formerly deactivated ones included.
- [x] 6.4 A user never gets another user's data: a session token of one user gives only their own profile.
- [x] 6.5 Sign-in, lock, sign-out and password reset work as before.
- [x] 6.6 `just check` and `just test-all` pass.
