---
paths:
  - "CHANGELOG.md"
  - "docs/releases/**"
  - "pyproject.toml"
---

# Versioning

Product versions and releases. Neighbours: `docs.md` for doc editions (not product versions),
`config.md` for the version's home.

## Rules

- SemVer computed from Conventional Commits since the last `v*` tag
  (`.claude/skills/release/scripts/next_version.py`): `feat` → minor, `fix`/`perf` → patch, a breaking
  change (`!` or `BREAKING CHANGE:`) → major, and below 1.0 → minor. Other types make no release.
- `1.0.0` only by the user's explicit command.
- One source of the version: root `pyproject.toml` `[project] version`. Other manifests do not carry it
  (`backend/pyproject.toml` and `frontend/package.json` stay `0.0.0`).
- Releases only through `/release`: it bumps the version, writes the CHANGELOG section and the release
  note, commits `chore(release): vX.Y.Z`, tags and pushes.
- The CHANGELOG is for users: Keep a Changelog headings (Added, Changed, Fixed, Removed, Security), plain
  language, no internal names.
- Release notes `docs/releases/vX.Y.Z.md`: «What's new», «Fixes», «Breaking changes», «Under the hood»,
  «How to update» only when the user has to act.

## Never

- Never change the version, `CHANGELOG.md` or a release note outside `/release`.
- Never edit a published release note; a correction goes into the next one.

Enforced by: the commit preflight (version changes outside a release), `next_version.py`.
