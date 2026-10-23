# UI as a React + TypeScript SPA

Id: 0002 · Date: 23.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context

Harness interview R4-Q1. The UI is in Russian and talks to the FastAPI backend.

## Decision

A React + TypeScript single-page app built with Vite, with pnpm, Vitest, ESLint, Prettier and tsc
strict; its API client is generated from the backend's OpenAPI schema.

## Alternatives

Server-rendered Jinja + HTMX (the recommendation); npm instead of pnpm; Biome instead of ESLint and
Prettier.

## Reason

Not given.
