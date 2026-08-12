# Contributing to Nomos

Thanks for your interest! This is a solo project but community contributions are welcome.

> **By submitting a contribution, you agree to the [Contributor License Agreement](CLA.md).**
> You retain copyright over your own contributions but grant the project owner
> a perpetual license to use them. See [`CLA.md`](CLA.md) for the full terms.

## Workflow

1. **Open an issue** first to discuss what you'd like to change
2. **Fork** the repo
3. **Create a branch** named `issue-XX-description` (e.g. `issue-42-fix-speaker-budget`)
4. **Make your changes**
5. **Run tests**: `python -m pytest tests/ -v`
6. **Submit a PR** against `main` — by opening the PR you accept the CLA

## Commit Style

- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Reference the issue: `Issue #42: fix budget overflow edge case`
- One commit per logical change

## Releases

- Releases are automated with [release-please](https://github.com/googleapis/release-please)
  (python release type). It consumes the conventional-commit prefixes above, so
  **semver-relevant changes must use `feat:` / `fix:` / `refactor:` / `perf:` /
  `revert:`** — this is now a mechanical requirement, not a style suggestion.
- After a releasable merge to `main`, a `chore(main): release nomos X.Y.Z` pull
  request opens automatically. Merge it as-is: on merge, release-please tags
  `vX.Y.Z`, publishes the GitHub release with generated notes, and the GHCR
  `publish-image` workflow builds and pushes the multi-arch images.
- **Do not hand-edit `CHANGELOG.md`** — release-please owns it.
- **Do not create tags or GitHub releases manually** — let the release PR do it.

## Labels Guide

| Label | Meaning |
|-------|---------|
| `bug` | Something isn't working |
| `enhancement` | New feature or request |
| `documentation` | Docs improvements |
| `good first issue` | Good for newcomers |
| `testing` | Test coverage |
| `research` | Theoretical or experimental |
| `osf` | OSF preregistration related |
| `book` | Book chapter or appendix |
| `cleanup` | Refactoring, debt |
| `meta` | Process / project management |

## Code Standards

- **No comments in code** — let the code speak; use docstrings for public APIs
- **Type hints** required for all public functions
- **Imports**: stdlib → third-party → local, one blank line between groups
- **Tests**: every new feature needs at least one test
- **No neural networks** in governance code — the layer must be fully algorithmic

## Where Things Live

| Path | Contents |
|------|----------|
| `src/nomos/` | Reference implementation — speaker, contracts, identity, TEE sim, audit log, runner |
| `book/` | Theory — chapters 1–4, appendices, review responses |
| `docs/` | MkDocs site — ADRs, API reference, server endpoints |
| `docs/adr/` | Architectural decision records — **read [ADR 0001](docs/adr/0001-modular-monolith-and-atomic-governance-gate.md) before proposing topology changes** |
| `gov-budget-proof/` | Lean 4 formal proofs |
| `examples/` | `.parliament` DSL configs |

## Questions?

Open a discussion or check the [README](README.md) and [book/](book/) for the theory.
