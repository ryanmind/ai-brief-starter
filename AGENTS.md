# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: entry point for feed fetching, summarization, ranking, and Markdown report generation.
- `src/config.py`: shared constants and environment parsing helpers; keep pipeline knobs centralized here.
- `scripts/`: operational tools (`notify_feishu.py`, `report_quality_check.py`, `source_health_check.py`).
- `tests/`: `pytest` suite for text utilities, fact checks, resilience, and script-level quality checks.
- `reports/`: runtime outputs (for example `latest.md`, health reports); treat as generated artifacts.
- `TEMPLATE.md`: template standard file and must not be modified; adapt output only through generation logic.
- `docs/`: MkDocs documentation source files; edit Markdown files here for the documentation site.
- `mkdocs.yml`: MkDocs configuration; update navigation and theme settings here.
- `.github/workflows/`: CI schedules for daily brief generation, source-health checks, and docs deployment.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create/activate local environment.
- `pip install -r requirements.txt`: install runtime, test, and documentation dependencies.
- `python main.py`: run the full brief pipeline locally and write outputs to `reports/`.
- `python -m pytest tests/ -v`: run all unit tests.
- `python scripts/report_quality_check.py reports/latest.md --autofix`: enforce/repair report format (summary/key points and related checks).
- `python scripts/source_health_check.py --output reports/source_health.md`: audit source availability and diversity.
- `mkdocs serve`: start local documentation server with hot reload (http://127.0.0.1:8000).
- `mkdocs build --strict`: build documentation site; fail on warnings.

## Coding Style & Naming Conventions
- Target Python 3.11, 4-space indentation, and clear type hints on non-trivial functions.
- Use `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants/env defaults, `test_*.py` for tests.
- Prefer small, composable helpers in `main.py`; move shared thresholds and patterns to `src/config.py`.
- Keep user-facing copy concise and Chinese-compatible (the brief output is Chinese-first).

## Data Cleaning Rules
- Use LLM-based processing for data cleaning tasks.
- Do not add or maintain Python 3 rule-based cleaning logic for new or updated cleaning flows.

## Testing Guidelines
- Framework: `pytest`.
- Add regression tests for every bug fix; keep tests deterministic (use `tmp_path` and `monkeypatch` for env/file behavior).
- No hard coverage gate is configured; changed logic should be covered by focused unit tests before PR.

## Commit & Pull Request Guidelines
- Follow Conventional Commits used in history: `fix(scope): ...`, `feat(scope): ...`, `refactor: ...`, `test: ...`, `ci: ...`, `chore: ...`.
- Keep scope aligned with module/domain (for example `pipeline`, `fetch`, `quality`, `tests`).
- PRs should include: purpose, key changes, risk/rollback notes, and validation commands run.
- When output format changes, attach a short sample from `reports/latest.md` (or screenshot) for reviewer clarity.

## Security & Configuration Tips
- Never commit API keys or webhook URLs; use GitHub Actions Secrets or local environment variables.
- `QWEN_API_KEY` is required for pipeline runs; Feishu and Kimi keys are optional integrations.
