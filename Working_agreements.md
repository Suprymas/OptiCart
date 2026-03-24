# Barboleta Working Agreements

## Purpose

This document defines how we collaborate so the team can move fast with clarity, quality, and respect.

## Team Principles

- Be clear, kind, and direct in communication.
- Assume positive intent and ask questions early.
- Raise blockers quickly; do not stay blocked alone.
- Prefer small, incremental improvements over big risky changes.

## Communication

- Share daily progress and blockers in the team channel.
- For decisions that affect architecture, write a short note in `docs/`.
- Use asynchronous communication by default; use calls for urgent issues.
- Respond to team questions within one business day.

## Branching and Commits

- Main development branch: `develop`.
- Create feature branches using:
  - `feature/...`
  - `fix/...`
  - `docs/...`
- Use Conventional Commits:
  - `feat: ...`
  - `fix: ...`
  - `docs: ...`
  - `chore: ...`
  - `test: ...`
- Keep commits focused and small.

## Pull Requests

- Open PRs early (draft is fine) to show direction.
- Keep PRs reasonably small and reviewable.
- Include:
  - What changed
  - Why it changed
  - How it was tested
- At least one approval is required before merge.
- Address review comments before merging.

## Definition of Done

A task is done when all of the following are true:

- Code is implemented and readable.
- Local run works via Docker (`docker compose up --build`).
- Relevant docs are updated.
- No obvious unresolved errors in logs.
- PR is reviewed and approved.

## Code Quality

- Follow existing project structure and conventions.
- Avoid premature optimization.
- Add comments only where logic is non-obvious.
- Prefer explicit, maintainable code over clever shortcuts.

## Testing and Validation

- Verify changes locally before opening PR.
- For backend changes, test main API flow manually.
- For infra changes, verify containers start and services are reachable.
- Add automated tests as the testing stack is introduced.

## Environment and Security

- Do not commit secrets.
- Use `.env.example` as the source of required variables.
- Keep local `.env` private.
- Use sample/test data in development only.

## Documentation

- Update documentation when behavior or setup changes.
- Keep docs concise and actionable.
- Prefer one source of truth for each process.

## Conflict Resolution

- Resolve technical disagreements with:
  - Clear options
  - Trade-offs
  - A timeboxed decision
- If unresolved, escalate to the project lead for final decision.

## Continuous Improvement

- Review these agreements at the end of each sprint.
- Adjust based on what is helping or slowing the team.
