# Proposal

## Why

Since the concept change of 28.10.2026 (`docs/prd.md` v0.4, ADR 0023) the app is a personal tool: one
person connects their own mailboxes and sees their own project trees. The organization layer of task 0.2
— an organization name at registration, administrators, employees, invitations, members, deactivation —
now stands between a visitor and their first project and has no user. Task 1.1 «Personal accounts» of
`docs/plan.md` removes it before mailboxes, chains and projects are built on top of it.

## What Changes

- **BREAKING** Registration takes a name, an email and a password; there is no organization name. The
  registrant becomes an individual user, not an administrator (FR-1…FR-3).
- **BREAKING** Invitations, the members list, roles, deactivation and reactivation are removed together
  with their pages «Участники» and invitation acceptance and their API (FR-9…FR-16, FR-18, FR-19 removed).
- The access boundary is per user: every piece of data belongs to one user, and a user never sees another
  user's data. FR-18 «Organizations never see each other» is replaced by FR-21 «Users never see each
  other».
- Sign-in, the lock, sessions, password reset, protected pages and cross-site protection keep their
  behavior; their wording loses organizations, roles and deactivation (FR-4, FR-6, FR-7, FR-8, FR-17,
  FR-20). FR-5 does not change.
- The signed-in user's profile shows the name and the email; there is no organization or role.
- Existing users stay as individual accounts with the same email, password and confirmation; formerly
  deactivated users can sign in again.
- The glossary, the data-access and database rules and the harness texts lose organizations,
  administrators, employees, members and invitations.

Out of scope:

- Mailboxes, reply chains, projects and their owner filter — later tasks of stage 1.
- Changing the password or the email while signed in, deleting an account, blocking an account — `docs/ideas.md`
  «Account settings».

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `organization-registration`: FR-1 (renamed «Register a user»)…FR-3 register an individual user instead of
  an organization.
- `sign-in`: FR-4, FR-6, FR-7, FR-8 lose the organization, the administrator role and deactivation.
- `access-boundary`: FR-17 and FR-20 lose members and invitations; FR-18 and FR-19 are removed; FR-21
  «Users never see each other» is added.
- `invitations`: FR-9…FR-12 removed; the capability is retired.
- `organization-members`: FR-13…FR-16 removed; the capability is retired.

## Impact

- Invariants: «Access boundary» — the owner of every piece of data becomes one user instead of an
  organization with roles (decided by the user, ADR 0023). No other invariant is touched.
- Backend: modules `accounts`, `auth`, `invitations` (removed), `app/platform` (auth context, validation
  messages); a new Alembic migration dropping organizations, invitations, roles and deactivation.
- API: `POST /api/v1/auth/registrations` loses `organization_name`; `GET /api/v1/auth/me` loses
  `organization` and `role`; `/api/v1/invitations/*` and `/api/v1/members/*` are removed. The SPA client
  is regenerated.
- SPA: registration form, start page, guards; pages «Участники» and invitation acceptance removed.
- Docs: `docs/domain.md` glossary, requirements map and «Cancelled numbers»; `docs/architecture.md`;
  `.claude/rules/data-access.md`, `database.md` and the other rules and harness texts that name
  organizations; `openspec/config.yaml` context.
