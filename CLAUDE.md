# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Brief Starter is an automated AI news briefing generator that runs daily via GitHub Actions. It fetches RSS feeds, filters for primary AI-related content, uses LLM (Qwen) for ranking/summarization, performs quality checks, and publishes to Feishu/WeChat with MkDocs documentation archival.

**Core Pipeline**: RSS Fetch → Primary Source Filter → AI Topic Filter → LLM Ranking/Summary → Chinese Localization → Quality Check → Markdown Report → Notification → Docs Archive

## Architecture

### Modular Structure (Post-Refactor)
- `main.py` (375 lines): Thin entry point that orchestrates the pipeline and exports backward-compatible APIs for tests
- `src/config.py`: Single source of truth for all configuration constants and environment variable parsing
- `src/models.py`: NewsItem dataclass definition for type-safe data structures
- `src/feed.py`: RSS/Twitter/GitHub feed fetching with Nitter fallback and TwitterAPI.io integration
- `src/filters.py`: Primary source filtering, AI topic filtering, deduplication, and per-domain quota enforcement
- `src/llm.py`: LLM interaction (chat, JSON extraction, ranking, localization, title completion)
- `src/report.py`: Report rendering, quality checks, and final output generation
- `src/text_utils.py`: Text processing utilities (cleaning, fact-checking, key point normalization, etc.)
- `scripts/`: Operational tools (Feishu/WeChat notification, quality checks, source health audits, docs syncing)
- `sources.txt`: RSS feed source list (supports RSS URLs, X/Twitter handles, GitHub changelog URLs)
- `reports/`: Runtime output directory (gitignored, preserved via GitHub Actions artifacts and cache)

### Key Design Patterns
- **Fail-open philosophy**: Quality checks warn but don't block publication (`QUALITY_CHECK_FAIL_OPEN=1`)
- **Strict fact mode**: LLM-generated summaries are validated against source text; falls back to extractive summaries if overlap is too low
- **Multi-layer filtering**: Primary source whitelist → AI topic keywords → per-domain limits → cross-day deduplication
- **Graceful degradation**: Nitter multi-instance probing, TwitterAPI.io fallback, GitHub changelog feed fallback to releases.atom

## Development Commands

### Environment Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Running Locally
```bash
# Full pipeline (requires QWEN_API_KEY)
python main.py

# Quality check with auto-fix
python scripts/report_quality_check.py reports/latest.md --autofix

# Source health audit
python scripts/source_health_check.py --output reports/source_health.md
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_resilience.py -v

# Run with coverage (if pytest-cov installed)
python -m pytest tests/ --cov=src --cov=main --cov-report=term-missing
```

### Documentation
```bash
# Local preview with hot reload
mkdocs serve

# Build static site (fail on warnings)
mkdocs build --strict
```

## Configuration

### Required Secrets (GitHub Actions)
- `QWEN_API_KEY`: Alibaba DashScope API key (required)

### Optional Secrets
- `TWITTERAPI_IO_KEY`: TwitterAPI.io key for X/Twitter feed fallback
- `FEISHU_WEBHOOK_URL`, `FEISHU_APP_ID`, `FEISHU_APP_SECRET`: Feishu notification
- `SERVERCHAN_SENDKEY`: WeChat notification via Server酱

### Key Environment Variables
- `TOP_N` (default: 20): Number of items in final report
- `MAX_ITEMS` (default: 120): Maximum items to fetch before filtering
- `STRICT_FACT_MODE` (default: 1): Enable fact-checking with fallback to extractive summaries
- `FACT_OVERLAP_MIN` (default: 0.55): Minimum overlap ratio for generated summaries
- `HISTORY_DEDUP_DAYS` (default: 2): Days to look back for deduplication
- `STRICT_PRIMARY_ONLY` (default: 1): Filter out second-hand media sources
- `STRICT_AI_TOPIC_ONLY` (default: 1): Filter out non-AI topics

See `src/config.py` for full list of configurable parameters.

## Critical Implementation Rules

### Code Style
- **Target**: Python 3.11
- **Indentation**: 4 spaces
- **Type hints**: Use on non-trivial functions
- **Naming**: `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants
- **Output language**: Chinese-first (the brief output is in Chinese)

### Data Cleaning Philosophy
**IMPORTANT: Use LLM-based processing for data cleaning tasks.** Do not add or maintain Python rule-based cleaning logic for new or updated cleaning flows. The project philosophy is to leverage LLM capabilities rather than maintain complex regex/heuristic rules. This is a core architectural decision.

### Backward Compatibility
`main.py` exports many functions from `src/*` modules to maintain backward compatibility with existing tests and scripts. When refactoring:
1. Keep exports in `main.py` until all references are migrated
2. Update tests to import from `src.*` modules directly when possible
3. Do not break the `main.py` API surface without checking test dependencies

### Data Model
All news items use the `NewsItem` dataclass defined in `src/models.py`:
- Type-safe with clear field definitions
- Supports conversion to/from dict for backward compatibility
- Fields: title, link, summary, published, dedupe_link, score, brief, details, impact, key_points

### Testing Philosophy
- Add regression tests for every bug fix
- Use `tmp_path` and `monkeypatch` for deterministic tests
- Mock external dependencies (LLM calls, network requests) in unit tests
- `test_resilience.py` covers edge cases (timeouts, LLM failures, quality check failures)

### Quality Checks
The quality check system (`scripts/report_quality_check.py`) validates:
- Title completeness (no missing subjects like "release: 4.6.3")
- Key points format (2-3 bullet points, max 28 chars each)
- No second-hand domain links in sources
- No weak placeholder phrases

Quality checks run automatically in the pipeline and can auto-fix issues with `--autofix`.

## Common Pitfalls

### 1. Global Mutable State
`_twitterapi_io_cache` and `_nitter_alive_cache` have been encapsulated in the `TwitterFeedCache` class. Use `clear_twitter_caches()` function to clear caches in tests to avoid cross-test pollution.

### 2. Fact-Check Configuration
`FACT_OVERLAP_MIN` and `STRICT_FACT_MODE` are read from environment but also monkeypatched in tests. When modifying fact-checking logic, ensure both `src/config.py` and `main.py` wrapper functions are updated.

### 3. LLM Prompt Changes
LLM prompts are embedded in `src/llm.py`. Changes to prompts can significantly affect output quality. Always test with real API calls (not just mocks) before merging prompt changes.

### 4. Markdown Template
`TEMPLATE.md` is the canonical template and must not be modified. Adapt output only through generation logic in `src/report.py`.

### 7. Dependencies Locked with Upper Bounds
`requirements.txt` specifies both lower and upper bounds for all major dependencies (e.g., `openai<2.0.0`, `feedparser<7.0.0`, `python-dateutil<3.0.0`) to prevent unexpected breaking changes. Test thoroughly when upgrading dependencies.

### 8. Sources File Format
`sources.txt` supports multiple formats:
- Standard RSS URLs
- X/Twitter handles (e.g., `https://x.com/openai`) - auto-converted to Nitter RSS
- GitHub changelog URLs (e.g., `.../blob/main/CHANGELOG.md`) - auto-converted to Atom feed
- GitHub commit links are filtered out by default; only releases/announcements are kept

## GitHub Actions Workflow

The daily workflow (`.github/workflows/daily.yml`) runs at 07:30 Beijing time (23:30 UTC) and:
1. Validates required secrets (fails fast if `QWEN_API_KEY` missing)
2. Installs dependencies
3. **Runs tests first** (safety gate before generation)
4. Restores deduplication cache from previous runs (GitHub Actions cache)
5. Generates daily brief
6. Saves updated deduplication cache (preserves history across runs)
7. Syncs to docs/ and commits (updates MkDocs site)
8. Uploads artifact (preserves reports/ even though gitignored)
9. Notifies Feishu/WeChat
10. Sends failure alerts if any step fails (with detailed step tracking)

**Concurrency control**: Only one workflow runs per branch at a time (`cancel-in-progress: true`).

**Cache strategy**: The deduplication index (`reports/history_index.json`) is cached across workflow runs to enable cross-day deduplication even though `reports/` is gitignored.

## Commit Message Format

Follow Conventional Commits:
- `feat(scope): description` - New features
- `fix(scope): description` - Bug fixes
- `refactor(scope): description` - Code refactoring
- `test(scope): description` - Test changes
- `docs(scope): description` - Documentation changes
- `ci(scope): description` - CI/CD changes
- `chore(scope): description` - Maintenance tasks

Common scopes: `pipeline`, `fetch`, `quality`, `tests`, `docs`, `ci`

## Security Notes

- Never commit API keys or webhook URLs
- All secrets must be in GitHub Actions Secrets or local environment variables
- `sources.txt` and prompt strategies are kept private (use private repo)
- SHA256 is used for deduplication hashing (non-security context)
