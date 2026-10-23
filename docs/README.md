# Documentation

Updated 23.10.2026

Product docs follow spec-driven development: why and what → requirements → how → why chosen → what next.
Open only what the task needs.

| Document | What is in it | Open it when |
|---|---|---|
| [prd.md](prd.md) | Problem, users, value, principles, user flow, stages, metrics, risks | You need to know what the product is for, or whether a change fits it |
| [domain.md](domain.md) | Glossary, requirements map, lifecycles, explanations and examples, data and privacy | You need a term, the FR numbers of a capability, or a worked example |
| [../openspec/specs/](../openspec/specs/) | Requirements `FR-N` with scenarios, one spec per capability | You change or test behavior |
| [architecture.md](architecture.md) | Implementation status, components, repository structure, layers, data model, API, deploy, security | You write or review code |
| [tech.md](tech.md) | Stack with reasons, dev environment and checks, environment variables, techniques | You add a dependency, a command or an env var |
| [decisions.md](decisions.md) | Index of the decisions; each one is an ADR in [adr/](adr/README.md) | You need to know why something is the way it is |
| [plan.md](plan.md) | Tasks with «Done when» | You start or finish a task |
| [ideas.md](ideas.md) | Ideas not planned yet; the technical backlog | You have an idea, or plan the next task |
| [tech-debt.md](tech-debt.md) | Things that work wrong now: bugs outside the task, weak tests, broken tooling | You find a defect outside your task |
| [setup.md](setup.md) | Non-code tasks: accounts, servers, demo | You prepare an environment or a demo |
| [guide/](guide/README.md) | Knowledge base: how each part works and how to change it | You change a part of the code for the first time |
| [journal/](journal/README.md) | One note per change: questions, decisions, mistakes | You need the history of a change |
| [releases/](releases/README.md) | Release notes for users, one per version | You prepare or read a release |

The agent harness (rules, skills, agents) is described in `CLAUDE.md` and `.claude/harness.md`, not here.
