# Fix of the backend image: uv from PyPI

Date: 29.10.2026 · Task: - · Change: fix-uv-from-pypi

## Goal

After task 1.2 was merged, the user ran `just dev` and the build failed on a DNS error to `ghcr.io`. Make the
backend dev image less dependent on external registries. A tooling fix on the branch `build/uv-from-pypi`: no
plan task and no OpenSpec change; the product behavior is not touched.

## What was done

- **Symptom.** `docker compose up --build` failed at `docker/backend.Dockerfile` line 4,
  `COPY --from=ghcr.io/astral-sh/uv:0.9.3 /uv /usr/local/bin/uv`, with «failed to fetch anonymous token …
  lookup ghcr.io: no such host».
- **Cause found.** At that moment the host DNS resolved nothing: `nslookup ghcr.io` timed out, and
  `registry.npmjs.org` also failed in the frontend container. The network had the DNS suffix
  `sigma.sbrf.ru`. Running with `--no-build` did not help: the backend command's `uv sync` tried to download
  `cryptography` and the frontend's corepack tried to download pnpm, and both need the network. A few minutes
  later DNS worked again and `docker compose up --build` succeeded.
- **Check of the whole stack in the built-in browser** on `http://localhost:5173` (the full stack in
  Docker): a throwaway user `flow-dev-check@example.test` registered and confirmed by the Mailpit link;
  `just demo-mail` loaded 43 messages; connecting `greenmail`, port 3143, `anna@demo.test` went from
  «Ожидает чтения» to «Прочитан 29.10.2026, 18:02»; «Переписка» listed 7 chains; the chain «Смета на ремонт
  офиса» showed its emails oldest first with «Тема:»; `just demo-mail status` still showed 5 and 6 unread.
  The throwaway user stays in the dev database.
- **Diagnosis (case D, tooling).** No product behavior, no spec. `ghcr.io` was used only on that Dockerfile
  line.
- **Fix by `code-writer`.** Line 4 is now `RUN pip install --no-cache-dir uv==0.9.3`; the pin 0.9.3 is
  unchanged. No tests exist for the Dockerfile.
- **Verification.** `docker compose build backend` succeeded; `docker run --rm vibecoding-backend uv
  --version` printed `uv 0.9.3`; the recreated backend answered `/api/v1/health` with 200 and the SPA with
  200; `just check` all PASS.
- **Docs.** `docs/tech.md` «Stack», the uv row, now names the PyPI install and links
  [ADR 0050](../adr/0050-the-backend-dev-image-installs-uv.md).

## Key questions to the AI

The digest holds no questions the user put to the AI in this fix, only the choice below, asked by the AI.

- Replace `ghcr.io`? The AI explained that this outage blocked every registry and a different registry would
  not have helped, but that a PyPI install removes one external registry. Answer: «Перейти на PyPI».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| The backend dev image installs uv 0.9.3 from PyPI (pip install) instead of copying it from the ghcr.io/astral-sh/uv image | keep COPY --from=ghcr.io/astral-sh/uv:0.9.3 | Пользователь выбрал «Перейти на PyPI» после того, как just dev упал на DNS до ghcr.io | [human] |

## Mistakes and lessons

- **The fix does not cure the outage that triggered it.** With no DNS at all every registry fails, so the
  stack still cannot start; the change only removes one external registry from the build.
- **A rerun without the build is no workaround:** `--no-build` still needs the network at start (`uv sync`,
  corepack). The first signal was one DNS lookup (`nslookup ghcr.io`); checking it first would have separated
  a network outage from a Dockerfile defect.
- **Nothing tests the Dockerfile,** so the fix was checked by hand: a build, the `uv --version` output, the
  health endpoint and `just check`.

## What remains

- The build still needs Docker Hub (`python:3.12-slim`) and PyPI, and the containers' start needs PyPI
  (`uv sync`) and npm (corepack pnpm). With no DNS at all the stack still cannot start; only the host-side
  tools can.
- In the main checkout's `.env`, `MAILBOX_ENCRYPTION_KEY` and `DEMO_MAIL_PASSWORD` are still missing.
- The throwaway user `flow-dev-check@example.test` stays in the dev database.
- The note is written before the commit; the commit goes through `/commit`.
