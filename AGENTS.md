# AGENTS Guide for SSMD

This file is for agentic coding assistants working in this repository. It summarizes how
to build, lint, and test, along with key style rules.

## Repo Layout

- `ssmd/` contains the library source code.
- `tests/` contains pytest-based unit tests.
- `pyproject.toml` defines tooling and configuration.

## Quick Setup

Normally not needed

- Install dev dependencies:
  - `uv pip install -e .[dev]`
- Install optional SSML-maker integration tests:
  - `uv pip install -e .[integration]`
- For spaCy-backed sentence detection tests:
  - `uv pip install -e .[spacy]`

## Test Commands

- Run the full suite:
  - `pytest`
- Run a single test file:
  - `pytest tests/test_document.py`
- Run a single test case or test function:
  - `pytest tests/test_document.py::TestDocumentListInterface::test_setitem`
- Run tests with coverage:
  - `pytest --cov=ssmd`

## Lint / Type Check

- Ruff lint (uses `tool.ruff` in `pyproject.toml`):
  - `ruff check .`
- Ruff format (if you choose to auto-format):
  - `ruff format .`
- pre-commit
  - `pre-commit run --all-files`
- Mypy type check (uses `tool.mypy` config):
  - `mypy ssmd`

## Formatting & Style

- Line length: 100 characters (see `[tool.ruff]`).
- Prefer f-strings for string interpolation.
- Keep docstrings for public classes, methods, and helpers.
- Maintain existing module-level docstrings.
- Use dataclasses where the codebase already uses them.
- Avoid adding inline comments unless necessary.
- Match existing spacing and blank-line conventions.

## Imports

- Use absolute imports within the `ssmd` package (e.g., `from ssmd.parser import ...`).
- Keep standard library imports first, then third-party, then local.
- Ruff’s `I` rule enforces import ordering.
- Avoid unused imports; ruff checks this.

## Git

- Use never git commands to alter files or commiting code, this is manually done be the
  user!

## Versioning

- package versioning is set automatically by git tags

## Types & Annotations

- Use type hints for new public functions and classes.
- Follow current typing style: `str | None` instead of `Optional[str]`.
- Mypy settings are relaxed but still check untyped defs; be consistent.
- Prefer `list[str]`/`dict[str, T]` over `List`/`Dict`.
- Use `TYPE_CHECKING` to avoid runtime import cycles.

## Naming Conventions

- Functions and variables: `snake_case`.
- Classes and exceptions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Private helpers: prefix with `_`.

## Error Handling

- Raise `ValueError` for invalid user input or malformed SSML/SSMD.
- Use explicit branches for invalid cases rather than silent fallbacks.
- Preserve existing error messages where behavior is user-facing.

## Parsing & Formatting Guidance

- Keep parsing logic deterministic; avoid hidden global state.
- When refactoring parsers, preserve ordering and token precedence.
- Avoid changing SSML/SSMD output semantics unless explicitly requested.
- Keep conversions centralized in shared helpers where possible.

## Testing Guidance

- Prefer targeted tests in `tests/` that assert exact output strings.
- Update or extend tests when changing parsing or formatting behaviors.
- Keep tests deterministic (no random inputs, no network).

## Documentation

- `docs/` contains the Sphinx documentation sources.
- Update relevant `.rst` files when changing public APIs or syntax.
- Build docs locally with `python docs/make.py html` if needed.

For Codecrate reconstruction checks, run
`python tools/verify_reconstruction.py SOURCE_ROOT RECONSTRUCTED_ROOT`. The checker
compares the runtime, test, build, and documentation artifact inventory covered by
`.codecrate.toml` and reports SHA-256 content changes.

## Specification Reference

- `SPECIFICATION.md` defines the SSMD syntax and mapping rules.
- Use it to validate parser or formatter changes.
- Check it when modifying prosody, breaks, voice, or annotation behavior.

## Notes

- `pyproject.toml` configures pytest, ruff, mypy, and coverage.
- The repo targets Python >= 3.10 and is tested up to 3.13.
- Keep public API changes minimal and well-documented.
