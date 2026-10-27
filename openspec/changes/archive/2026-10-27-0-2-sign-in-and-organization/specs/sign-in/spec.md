# Spec Delta

## Purpose

Lets a member of an organization sign in with email and password, keeps them signed in for a limited
time, and lets them regain access by email when the password is forgotten.

## ADDED Requirements

### Requirement: FR-4 Sign in with email and password

A confirmed, active user SHALL sign in with their email, compared without regard to case and
surrounding spaces, and their password. A wrong password and an unknown email SHALL give the same
answer, «Неверный email или пароль», so the answer never tells whether an email is registered.

#### Scenario: Successful sign-in
- **WHEN** Анна, a confirmed administrator of «ООО Ромашка», signs in with « ANNA@romashka.test » and her password
- **THEN** she is signed in and lands on the start page with her name «Анна Петрова» and the organization «ООО Ромашка» shown

#### Scenario: Wrong password or unknown email
- **WHEN** someone signs in as «anna@romashka.test» with a wrong password, or as «nobody@romashka.test»
- **THEN** sign-in is refused with «Неверный email или пароль» in both cases

#### Scenario: Empty fields
- **WHEN** someone submits the sign-in form with an empty email or an empty password
- **THEN** sign-in is refused with «Укажите email и пароль» and no failed attempt is counted

### Requirement: FR-5 Lock sign-in after failed attempts

After 5 failed sign-in attempts for one email within 15 minutes, the app SHALL refuse every sign-in
for that email for 15 minutes, even with the right password. Attempts for an unknown email SHALL be
counted the same way. A successful sign-in or a completed password reset SHALL clear the count.

#### Scenario: The fifth wrong password locks sign-in
- **WHEN** someone enters a wrong password for «anna@romashka.test» 5 times within 10 minutes and then the right one
- **THEN** the sixth attempt is refused with «Слишком много попыток входа. Попробуйте через 15 минут»

#### Scenario: The lock ends
- **WHEN** 15 minutes have passed since the lock began and Анна signs in with the right password
- **THEN** she is signed in

#### Scenario: Failures spread over time do not lock
- **WHEN** someone enters a wrong password for «anna@romashka.test» 4 times, waits 16 minutes, then enters a wrong password once more
- **THEN** the next sign-in with the right password succeeds

#### Scenario: Another email is not affected
- **WHEN** sign-in for «anna@romashka.test» is locked and Борис signs in as «boris@romashka.test» with his password
- **THEN** Борис is signed in

### Requirement: FR-6 Session lifetime and sign-out

A sign-in SHALL start a session that lasts 14 days. Signing out SHALL end the session at once. An ended
or expired session SHALL be treated as signed out: a protected page sends the visitor to «Вход». A
session SHALL NOT be readable by the page's scripts.

#### Scenario: Sign-out
- **WHEN** Анна presses «Выйти» and then opens the page «Участники»
- **THEN** she sees the page «Вход»

#### Scenario: Expired session
- **WHEN** Анна signed in 15 days ago and opens the start page
- **THEN** she sees the page «Вход»

#### Scenario: Sign-out on one device keeps the other
- **WHEN** Анна is signed in on a laptop and a phone and signs out on the laptop
- **THEN** she stays signed in on the phone

### Requirement: FR-7 Request a password reset

A visitor SHALL request a password reset by entering an email. For a confirmed user, active or not,
the app SHALL send a reset link that is single-use and valid for 1 hour. The page SHALL show the same
answer whether or not the email belongs to a user: «Если такой email зарегистрирован, мы отправили на
него ссылку для сброса пароля».

#### Scenario: Reset requested for a registered email
- **WHEN** Анна requests a reset for «anna@romashka.test»
- **THEN** one reset email goes to «anna@romashka.test» and the page shows the common answer

#### Scenario: Reset requested for an unknown email
- **WHEN** someone requests a reset for «nobody@romashka.test»
- **THEN** no email is sent and the page shows the same common answer

#### Scenario: A new request replaces the earlier link
- **WHEN** Анна requests a reset twice and follows the link from the first email
- **THEN** the page shows «Ссылка недействительна или устарела»

### Requirement: FR-8 Set a new password by the reset link

Following a valid reset link, the user SHALL set a new password of 10–128 characters. Setting it SHALL
end all of the user's sessions and clear the sign-in lock. A deactivated user SHALL be able to set the
password but SHALL still be refused sign-in.

#### Scenario: Password reset ends old sessions
- **WHEN** Анна is signed in on her phone, follows a reset link 30 minutes after requesting it and sets «new-correct-horse-2»
- **THEN** her phone session ends, the old password is refused, and she signs in with «new-correct-horse-2»

#### Scenario: Expired or used reset link
- **WHEN** Анна follows a reset link 61 minutes after requesting it, or uses it a second time
- **THEN** the password stays the same and the page shows «Ссылка недействительна или устарела»

#### Scenario: Too short new password
- **WHEN** Анна follows a valid reset link and enters «short»
- **THEN** the password stays the same, the link stays valid, and the form shows «Пароль должен быть от 10 до 128 символов»
