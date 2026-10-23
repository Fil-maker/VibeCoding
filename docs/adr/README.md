# Architecture decision records

Updated 23.10.2026

One file per decision: `NNNN-<slug>.md`, numbered in order. The index with status is
[decisions.md](../decisions.md). An ADR is written by the decision draft script
(`.claude/skills/document/scripts/session_facts.py write-decisions`) after the user confirms it; its
reason is the user's words. A replaced ADR gets the status «Superseded by NNNN» and stays.

| ADR | Decision |
|---|---|
| [0001](0001-fastapi-backend.md) | Backend in Python with FastAPI |
| [0002](0002-react-spa.md) | UI as a React + TypeScript SPA |
| [0003](0003-postgresql.md) | PostgreSQL in Docker |
