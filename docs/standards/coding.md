# Coding Standards

These standards apply to the active auth control plane codebase.

## Python

- Keep modules small and bounded by context.
- Prefer explicit service functions and clear schema types over implicit side effects.
- Keep policy and enforcement logic readable and deterministic.
- Use comments sparingly and only where the intent is not obvious from the code.

## React

- Keep components oriented around visible user states.
- Favor straightforward state transitions over aggressive abstraction.
- Make loading, empty, error, and degraded realtime states explicit.
- Prefer design clarity over dashboard ornament.

## Repository Practices

- One commit should represent one clear idea.
- Keep the worktree clean between task boundaries.
- Update docs when behavior or the default runtime path changes.
- Preserve mock-first seams for auth, vault, and provider integrations.
