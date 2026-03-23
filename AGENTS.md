# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: entry point for feed fetching, summarization, ranking, and Markdown report generation.
- `src/config.py`: shared constants and environment parsing helpers; keep pipeline knobs centralized here.
- `src/llm.py`: LLM interaction (chat, JSON extraction, ranking, localization, multi-model review).
- `src/llm/cache.py`: LLM response caching.
- `src/llm/prompts.py`: external prompt template loader.
- `src/models.py`: NewsItem dataclass and serialization.
- `src/text_utils.py`: text cleaning, normalization, fact checking, deduplication utilities.
- `src/feed.py`: RSS/Atom feed fetching, source management.
- `src/filters.py`: AI topic filtering, source limits, history-based deduplication.
- `src/report.py`: Markdown rendering, category balance checks.
- `scripts/`: operational tools (`notify_feishu.py`, `report_quality_check.py`, `source_health_check.py`).
- `tests/`: `pytest` suite for text utilities, fact checks, resilience, and script-level quality checks.
- `reports/`: runtime outputs (for example `latest.md`, health reports); treat as generated artifacts.
- `TEMPLATE.md`: template standard file and must not be modified; adapt output only through generation logic.
- `docs/`: MkDocs documentation source files; edit Markdown files here for the documentation site.
- `mkdocs.yml`: MkDocs configuration; update navigation and theme settings here.
- `.github/workflows/`: CI schedules for daily brief generation, source-health checks, and docs deployment.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: create/activate local environment.
- `pip install -r requirements.txt`: install runtime dependencies only.
- `pip install -r requirements.txt -r requirements-dev.txt`: install runtime + test dependencies.
- `pip install -r requirements.txt -r requirements-docs.txt`: install runtime + docs dependencies.
- `python main.py`: run the full brief pipeline locally and write outputs to `reports/`.
- `python -m pytest tests/ -v`: run all unit tests.
- `python -m pytest tests/test_xxx.py -v`: run a single test file.
- `python -m pytest tests/test_xxx.py::test_func_name -v`: run a single test function.
- `python scripts/report_quality_check.py reports/latest.md --autofix`: enforce/repair report format (summary/key points and related checks).
- `python scripts/source_health_check.py --output reports/source_health.md`: audit source availability and diversity.
- `mkdocs serve`: start local documentation server with hot reload (http://127.0.0.1:8000).
- `mkdocs build --strict`: build documentation site; fail on warnings.

## Coding Style & Naming Conventions
- Target Python 3.11, 4-space indentation, and clear type hints on non-trivial functions.
- Use `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants/env defaults, `test_*.py` for tests.
- Prefer small, composable helpers in `main.py`; move shared thresholds and patterns to `src/config.py`.
- Keep user-facing copy concise and Chinese-compatible (the brief output is Chinese-first).
- **Import organization**: Use `from __future__ import annotations` at top, group imports: stdlib, third-party, local (with blank line between groups).
- **Docstrings**: Use Google-style docstrings for public functions; include Args/Returns/Raises sections when applicable.
- **Error handling**: Prefer specific exception types; use fail-open pattern for non-critical errors (log warning, return default value).
- **Type hints**: Use `X | None` syntax (Python 3.10+) for nullable types, `list[X]` for generic containers.
- **Constants**: Group related constants in dataclasses or named tuples; use descriptive names (`BRIEF_MAX_CHARS` not `MAX`).
- **Logging**: Use `logger = logging.getLogger(__name__)` for each module; log structured data as `key=value` pairs.

## Content Generation Quality
- **关键点规则**：每条必须是完整句子，包含具体事实/数字/版本号/实体名称；不能是原文截断片段。
- **影响分析规则**：回答对行业/用户/技术格局的具体影响；避免"建议查看原文"等套话。
- **标题规则**：必须包含明确主体（公司/产品/人物）；版本号需写清"谁的什么版本"。
- Prompt 定义在 `src/llm.py` 的 `rank_and_summarize()` 和 `localize_items_to_chinese()` 中。

## Classification Rules
- 分类逻辑在 `scripts/render_latest_for_mkdocs.py` 的 `classify_item()` 中。
- 三类：模型进展（model）、论文研究（paper）、产品与行业（product）。
- **模型强关键词**：grok/claude/gpt-/gemini/llama/deepseek/mistral/qwen/chatgpt 等，出现即归类为模型进展。
- **论文关键词**：arxiv/论文/预印本/preprint，出现即归类为论文研究。
- 其余按分数计算归类。

## Multi-Model Review
- **审核流程**：每条资讯生成后，使用多个模型交叉验证真实性。
- **默认模型**：kimi-k2-0905, iflow-rome-30ba3b, kimi-k2。
- **投票机制**：至少 2 个模型通过才发布（可通过 `REVIEW_PASS_THRESHOLD` 配置）。
- **审核标准**：真实性（无幻觉）、完整性（标题有主体）、准确性（关键点是完整句子）、价值性（摘要有信息价值）。
- **配置项**：
  - `REVIEW_ENABLED=0`：禁用审核
  - `REVIEW_MODELS=模型1,模型2`：自定义审核模型
  - `REVIEW_PASS_THRESHOLD=2`：通过阈值
- 实现在 `src/llm.py` 的 `review_items_with_multi_model()` 中。

## Data Cleaning Rules
- Use LLM-based processing for data cleaning tasks.
- Do not add or maintain Python 3 rule-based cleaning logic for new or updated cleaning flows.

## Testing Guidelines
- Framework: `pytest`.
- Add regression tests for every bug fix; keep tests deterministic (use `tmp_path` and `monkeypatch` for env/file behavior).
- No hard coverage gate is configured; changed logic should be covered by focused unit tests before PR.
- **Test patterns**: Import from `main` (e.g., `from main import clean_text`) for backward compatibility; use `pytest.raises()` for exception tests.
- **Fixtures**: Use `tmp_path` for file operations; prefer `monkeypatch.setenv()` over `os.environ` manipulation.
- **Test naming**: `test_<function>_<scenario>` for clarity (e.g., `test_clean_text_strips_html`).

## Commit & Pull Request Guidelines
- Follow Conventional Commits used in history: `fix(scope): ...`, `feat(scope): ...`, `refactor: ...`, `test: ...`, `ci: ...`, `chore: ...`.
- Keep scope aligned with module/domain (for example `pipeline`, `fetch`, `quality`, `tests`).
- PRs should include: purpose, key changes, risk/rollback notes, and validation commands run.
- When output format changes, attach a short sample from `reports/latest.md` (or screenshot) for reviewer clarity.

## Security & Configuration Tips
- Never commit API keys or webhook URLs; use GitHub Actions Secrets or local environment variables.
- `IFLOW_API_KEY` is required for pipeline runs; Feishu and Kimi keys are optional integrations.
- Store secrets in `.env` (add to `.gitignore`) or GitHub Secrets; do not hardcode in source.

## Local Skill Routing
- Local project skill: `skills/ai-brief/SKILL.md`.
- Use this local skill when tasks involve this repo's scheduled AI brief workflow, including source ingestion, filtering, summarization, report generation, quality checks, docs sync, notifications, or related GitHub Actions.
- Read `skills/ai-brief/SKILL.md` before changing those areas, and follow its scope, guardrails, operating loop, and validation guidance.
- Do not use this local skill as a generic scheduled-job template outside this repository.

## Pipeline Architecture
- **Optimized pipeline** (default, `USE_OPTIMIZED_PIPELINE=1`): merges ranking/summarization into single LLM call, uses intelligent review (single-model for low-risk, multi-model for high-risk).
- **Legacy pipeline**: separate `rank_and_summarize` → `localize_items_to_chinese` → `enforce_titles_with_subject` → `review_items_with_multi_model` → `dedupe_selected_items` → `polish_markdown_with_llm`.
- Configurable via `USE_OPTIMIZED_PIPELINE` environment variable.

## Environment Variables Reference
| Variable | Default | Description |
|----------|---------|-------------|
| `IFLOW_API_KEY` | (required) | LLM API key |
| `LLM_MODEL` | `qwen3-coder-plus` | Model name |
| `MAX_ITEMS` | 120 | Maximum items to process |
| `TOP_N` | 20 | Final report item count |
| `FETCH_HOURS` | 24 | Lookback window for feeds |
| `USE_OPTIMIZED_PIPELINE` | 1 | Enable optimized pipeline |
| `REVIEW_ENABLED` | 1 | Enable multi-model review |
| `REVIEW_MODELS` | (see config) | Custom review models |
| `STRICT_FACT_MODE` | 1 | Enable fact validation |
| `LOG_LEVEL` | INFO | Logging verbosity |

## Code Organization Patterns

### Module Structure
Each `src/*.py` module should:
- Define `logger = logging.getLogger(__name__)` at module level
- Use clear type hints on all public functions
- Follow fail-open pattern for non-critical errors (log warning, return default)
- Export core functions; keep helpers private with `_` prefix

### main.py Re-exports
`main.py` serves as a backward-compatible API layer:
- Re-export all public functions from `src/*` modules
- Add wrapper functions for dict-based API if needed
- Keep `main.py` API stable; logic lives in `src/*`

### Data Classes
- Use `dataclasses` for structured data (see `src/models.py`)
- Add `from_dict()` / `to_dict()` / `from_dict_list()` / `to_dict_list()` class methods for serialization
- Keep serialization logic co-located with the model

### LLM Integration
- All LLM prompts stored externally in `src/llm/prompts/`
- Use `load_prompt()` to load templates
- Always implement fallback logic for LLM failures
- Log structured observability data (`key=value` format)

### Data Flow & Backward Compatibility
- Pipeline: feed fetch → filter primary → filter AI topic → apply source limits → deduplicate history → rank/summarize → review → dedupe → render
- `main.py` re-exports all `src/*` functions for backward compatibility
- Tests import from `main` to ensure API stability
- Environment variable parsing via `src/config.py` helpers (`int_env`, `float_env`, `parse_csv_env`)
