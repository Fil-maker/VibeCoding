# Spec Delta

## Purpose

Lets an administrator bring employees into the organization: an employee joins only by an invitation
sent to their email, never by the domain of their address.

## ADDED Requirements

### Requirement: FR-9 Invite an employee

An administrator SHALL invite a person by email. The app SHALL create an invitation to their
organization and email a link that is single-use and valid for 7 days. An invitation SHALL be refused
when the email belongs to a confirmed user of any organization. It SHALL also be refused when the
organization already has an open invitation for that email.

#### Scenario: Successful invitation
- **WHEN** Анна, the administrator of «ООО Ромашка», invites «boris@romashka.test»
- **THEN** an invitation for «boris@romashka.test» with the status «Отправлено» appears in her list, and one invitation email with the link goes to that address

#### Scenario: The email is already a user
- **WHEN** Анна invites «vera@lyutik.test», a confirmed user of the organization «Лютик»
- **THEN** no invitation is created and the form shows «Этот email уже зарегистрирован»

#### Scenario: A repeated invitation
- **WHEN** Анна invites «boris@romashka.test» a second time while the first invitation is open
- **THEN** no second invitation is created and the form shows «Приглашение на этот email уже отправлено»

#### Scenario: The domain does not grant membership
- **WHEN** a person with the email «gleb@romashka.test», which has no invitation, registers or signs in
- **THEN** they do not join «ООО Ромашка»

### Requirement: FR-10 Invitation status and resending

An administrator SHALL see the invitations of their organization, newest first. Each SHALL show its
email, the date it was sent and one status: «Отправлено», «Не отправлено», «Принято», «Отозвано» or
«Истекло». When the email could not be handed to the mail server, the invitation SHALL stay
«Не отправлено». The administrator SHALL be able to resend an open invitation. A resend SHALL send a
new link valid for 7 days, and the earlier link SHALL stop working.

#### Scenario: The mail server is unavailable
- **WHEN** Анна invites «boris@romashka.test» while the mail server refuses connections
- **THEN** the invitation exists with the status «Не отправлено» and the page shows «Не удалось отправить письмо. Попробуйте отправить ещё раз»

#### Scenario: Resending
- **WHEN** Анна presses «Отправить ещё раз» for the invitation of «boris@romashka.test» after the mail server is back
- **THEN** its status becomes «Отправлено», a new email goes out, and the link from any earlier email shows «Приглашение недействительно или устарело»

#### Scenario: An expired invitation
- **WHEN** Анна opens her list 8 days after inviting «boris@romashka.test», who never accepted
- **THEN** the invitation shows «Истекло» and no resend is offered for it

### Requirement: FR-11 Revoke an invitation

An administrator SHALL revoke an open invitation of their organization. Its link SHALL stop working at
once. Revoking an invitation that is not open SHALL change nothing.

#### Scenario: Revoking
- **WHEN** Анна revokes the invitation of «boris@romashka.test» and Борис then follows its link
- **THEN** the invitation shows «Отозвано» and Борис sees «Приглашение недействительно или устарело»

#### Scenario: Revoking an accepted invitation
- **WHEN** Анна tries to revoke the invitation that Борис has already accepted
- **THEN** the invitation stays «Принято» and Борис stays a member

### Requirement: FR-12 Accept an invitation

Following a valid invitation link SHALL show the organization name and the invited email. The person
SHALL join by giving their name (1–200 characters) and a password of 10–128 characters. They SHALL
become a confirmed, active employee of that organization and be signed in. The invitation SHALL become
«Принято».

#### Scenario: Successful acceptance
- **WHEN** Борис follows the link 3 days after the invitation, enters «Борис Иванов» and «boris-password-1»
- **THEN** he is signed in as an employee of «ООО Ромашка», and Анна sees his invitation as «Принято» and him in the members list

#### Scenario: A used, revoked, replaced or expired link
- **WHEN** Борис follows the link a second time after joining, or follows a revoked link, a link replaced by a resend, or a link 8 days old
- **THEN** no user is created and the page shows «Приглашение недействительно или устарело»

#### Scenario: The email became a user meanwhile
- **WHEN** «boris@romashka.test» is invited by «ООО Ромашка» and by «Лютик», joins «Лютик», and then follows the link of «ООО Ромашка»
- **THEN** he does not join «ООО Ромашка» and the page shows «Этот email уже зарегистрирован»
