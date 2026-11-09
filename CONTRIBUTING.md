# Contributing

## Setup

```bash
git clone <repo-url>
cd physiotherapy_database
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Testing

```bash
python -m pytest tests/ -q
```

All 43 tests must pass before submitting a PR.

## Code Style

- Follow PEP 8.
- Use type hints for new functions.
- Keep functions under ~50 lines where practical.
- All user-facing strings go through `lang.t()` (bilingual EN/RO).
- Log exceptions with `log.debug_exc(logger)` — never swallow silently.
- Use parameterized SQL — never string-interpolate user input.

## Commit Messages

Use conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`.

## Pull Requests

- One concern per PR.
- Include tests for new functionality.
- Update CHANGELOG.md.