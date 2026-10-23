# Domain

Version 0.1 · 23.10.2026

Changes in 0.1: skeleton; terms from the harness interview.

Last FR number: FR-0

## Contents

- [Requirements map](#requirements-map)
- [Glossary](#glossary)
- [Lifecycle of an assessment](#lifecycle-of-an-assessment)
- [Data and privacy](#data-and-privacy)
- [Non-functional notes](#non-functional-notes)
- [Cancelled numbers](#cancelled-numbers)

## Requirements map

Capability → its spec and FR numbers. A new FR number also goes into «Last FR number» above.

| Capability | Spec | FR |
|---|---|---|

No capabilities are specified yet.

## Glossary

| Term | Meaning |
|---|---|
| Organization | The company that uses the app; it has one or more administrators and employees |
| Employee | A user who sees only their own correspondence |
| Administrator | A user who sees all correspondence of their organization and gives consent to third-party analysis |
| Mailbox | An email account connected to the app read-only |
| Counterparty | An external person or company the organization corresponds with |
| Correspondence | The emails between the organization and a counterparty |
| Assessment | The sentiment of a counterparty computed from the correspondence, with its evidence |
| Evidence | The emails and phrases an assessment rests on |
| Analysis model | The engine and its version that computes an assessment; shown with the result |

TBD: how a counterparty is identified (address, domain, company).

## Lifecycle of an assessment

TBD.

## Data and privacy

- Email text and metadata are read from the mailbox and stored by the app; the mailbox is never changed.
- Email text leaves the app for a third-party service only after the administrator's consent.
- TBD: retention, deletion of a mailbox and its data.

## Non-functional notes

TBD.

## Cancelled numbers

None.
