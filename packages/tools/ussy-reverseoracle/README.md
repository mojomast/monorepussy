# ReverseOracle

Counterfactual code decision explorer. Generate and evaluate alternative implementations of past architectural decisions.

## Install

```bash
pip install -e .
```

## Usage

```bash
# Mark a decision point
reverseoracle mark ./my-repo abc123 --description "Chose Redis over Memcached for caching"

# List decision points
reverseoracle list-marks ./my-repo

# Analyze a decision
reverseoracle analyze ./my-repo --decision "Redis vs Memcached" --at-commit abc123

# Compare counterfactual against baseline
reverseoracle compare --counterfactual ./counterfactual/ --baseline ./my-repo

# Generate report
reverseoracle report --format html --output decision-audit.html
```

## Configuration

Create `.reverseoracle/config.yaml`:

```yaml
llm:
  provider: openai
  model: gpt-4
  base_url: https://api.openai.com/v1
  api_key_env: OPENAI_API_KEY

analysis:
  max_evolution_commits: 50
  test_timeout: 120
```
