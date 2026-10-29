# check_doc_links.py and check_doc_facts.py skip .claude/worktrees/

Id: 0042 · Date: 29.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.1.
- Organizations, invitations, members, roles and deactivation are removed from the backend, the SPA, the API and the schema; the user is the root owner.
- Migration 0003_personal_accounts drops invitations, organizations, organization_id of users/sessions/user_tokens, users.role and users.is_active; users, password hashes, confirmation, sessions and tokens stay. Downgrade recreates one organization per user named after users.name, every user administrator and active, organization_id of sessions and tokens from their user; invitations come back empty.
- Schema after 0003: users(id, email unique, name, password_hash, confirmed_at, created_at); sessions and user_tokens without organization_id.
- app/platform/auth_context.py: AuthContext holds user_id only; Role, require_administrator and current_admin are deleted.
- accounts: register (was register_organization) creates a user without an organization; repository add_user and delete_user (was add_organization_with_administrator, delete_organization); find_by_email is installation-wide, the other user queries filter by user_id; members router, service, Member, RoleChange schemas and accounts/domain.py are deleted.
- auth: TokenOwner removed, repository functions take a plain user_id; the is_active check and AccountDisabled/account_disabled are removed; Me is {user_id, name, email}.
- Removed API: every /api/v1/invitations and /api/v1/members route answers 404 like any unknown path; removed error codes account_disabled, invalid_invitation, invitation_exists, invitation_not_open, cannot_deactivate_self, last_administrator, member_inactive.
- RegistrationRequest is {name, email, password}; any other field, organization_name included, is refused with 422 validation_failed (RequestModel forbids extra fields).
- Every state-changing /api/ route still declares 403 because OriginGuardMiddleware answers forbidden_origin.
- Settings: invitation_lifetime_days / INVITATION_LIFETIME_DAYS removed; OrganizationName and the field message «Укажите название организации» removed; app/platform/pagination.py deleted.
- SPA: «Регистрация» has fields «Имя», «Email», «Пароль»; the start page shows the user's name and «Выйти»; features/members, features/invitations, RequireAdmin and isAdministrator are deleted; /members and /invitation fall to «Страница не найдена»; ui.module.css loses .muted; the client is regenerated.
- Tests: factories confirmed_user/unconfirmed_user and Account(email, password, name, user_id); employee and invitation factories deleted; test_migrations.py seeds task 0.2 data at revision 0002 and checks upgrade, sign-in of a formerly deactivated user after it, and downgrade; frontend test/appHarness.tsx ANNA is {user_id, name, email}; membersFixtures.tsx deleted.
- .claude/launch.json has a second configuration «spa (docker compose, local images)» running docker compose up --no-build, for working without network.

## Decision
check_doc_links.py and check_doc_facts.py skip .claude/worktrees/

## Alternatives
none recorded

## Reason
The user agreed: nested worktrees of other sessions are not part of this working copy, and their files broke the commit hook
