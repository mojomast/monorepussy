Build ReverseOracle — a CLI tool that generates and evaluates counterfactual implementations of past architectural decisions in git repositories.

IMPLEMENT EVERYTHING in the SPEC.md file attached. This is a Python CLI tool using:
- Click for CLI
- src/reverseoracle/ layout with pyproject.toml
- Dataclasses for data models
- httpx for LLM API calls (provider-agnostic, OpenAI-compatible)
- subprocess calls to git (no gitpython)
- No external code analysis deps (radon is optional)

Key features to implement:
1. `reverseoracle mark <repo> <commit> --description "chose X over Y"` — Mark a decision point, store in .reverseoracle/marks.json
2. `reverseoracle list-marks <repo>` — Show all marked decision points
3. `reverseoracle analyze <repo> --decision "X vs Y" --at-commit abc123` — Full pipeline: context reconstruction → counterfactual generation → evolution → evaluation → report
4. `reverseoracle compare --counterfactual ./cf/ --baseline ./repo` — Compare counterfactual against baseline
5. `reverseoracle report --format html --output report.html` — Generate formatted report from analysis

The context reconstructor must:
- Extract file contents at a specific commit via `git show <commit>:<path>`
- Identify interface files from the commit's changed files
- Find test files by convention (test_*.py, *_test.py)
- Extract commit messages as requirements context
- Parse requirements.txt / pyproject.toml for dependencies

The generator must:
- Build a structured prompt with interface contract, current implementation, tests, and alternative tech
- Call LLM via httpx (OpenAI-compatible API)
- Parse code blocks from LLM response
- Validate generated code with ast.parse
- Write to .reverseoracle/counterfactuals/<id>/

The evolution simulator must:
- Get post-decision commits touching relevant files
- For each commit, extract diff and ask LLM to apply intent to counterfactual
- Validate each evolution step
- Respect max_evolution_commits config limit

The evaluator must:
- Run pytest on both baseline and counterfactual with timeout
- Collect pass/fail/skip counts and timing
- Count LOC, function definitions, class definitions
- Parse imports for dependency count
- Generate diff summary

The reporter must support:
- text: terminal output with tables
- json: structured JSON
- html: styled HTML5 with tables and metrics

The LLM provider must:
- Support OpenAI-compatible API via httpx
- Allow base_url override for custom endpoints (Ollama, etc.)
- Read API key from environment variable
- Include a mock provider for testing

The marks storage must:
- Store in .reverseoracle/marks.json as JSON array
- Support add, list, and lookup operations
- Each mark has: id (uuid), commit, description, alternative, module_path, created_at

Config: .reverseoracle/config.yaml with llm, analysis, and generation sections.
Environment overrides: REVERSEORACLE_LLM_BASE_URL, REVERSEORACLE_LLM_MODEL, OPENAI_API_KEY.

Write comprehensive tests in tests/ for all modules. Use pytest with a mock LLM provider.
