# Circadia — Circadian Rhythm-Aware Development Environment 🌙☀️

> *Your tools should protect you when you're tired.*

Circadia adapts your development environment's behavior based on your estimated cognitive state. It uses circadian rhythm science — time of day, session duration, and typing patterns — to determine whether you're in a **green** (peak), **yellow** (cautious), **red** (impaired), or **creative** (evening flow) zone, then adjusts linter strictness, git operation gating, and deploy blocking accordingly.

## The Insight

Research shows developers inject **2-3x more defects** during circadian dips (late night, post-lunch). Current tools treat all hours the same — your linter is equally permissive at 2PM and 2AM. Circadia reframes developer fatigue as a **software quality problem**, not a wellness problem.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Check your current cognitive zone
circadia status

# Start a coding session (tracks duration)
circadia session start

# Install git hooks that block risky operations in yellow/red zones
circadia hooks install

# Check if a specific git operation is allowed right now
circadia hooks check force-push

# View linter configuration for your current zone
circadia linter

# View or edit configuration
circadia config --show
circadia config --set utc_offset_hours -5
```

## Cognitive Zones

| Zone | Icon | When | Behavior |
|------|------|------|----------|
| **Green** | 🟢 | Morning peak, well-rested | Standard rules, all operations allowed |
| **Yellow** | 🟡 | Post-lunch dip, moderate session | Enhanced linting, risky operations need confirmation |
| **Red** | 🔴 | Late night, long session | Maximum linting, deploy/force-push/hard-reset blocked |
| **Creative** | 🟣 | Evening flow state | Relaxed rules, creative work encouraged |

## Architecture

```
circadia/
├── zones.py       — Cognitive zone definitions (Green/Yellow/Red/Creative)
├── estimator.py   — Bayesian cognitive state estimation from time-of-day + session duration
├── config.py      — Configuration management (thresholds, git hooks, linter rules)
├── session.py     — Session tracking (start/end/duration)
├── hooks.py       — Git hook management (install/remove/check operations)
├── linter.py      — Zone-adaptive linter configuration
├── indicator.py   — Terminal zone indicator for shell prompts
└── cli.py         — Command-line interface (argparse)
```

### Bayesian Estimation

Circadia uses a simplified Bayesian model to estimate cognitive state:

1. **Prior**: Time-of-day probability derived from circadian research (peak performance ~10AM, nadir ~3AM)
2. **Likelihood**: Session duration modifier (fatigue increases with hours coded)
3. **Posterior**: Combined probability across all four zones

The dominant zone is selected from the posterior distribution, with a confidence score indicating how certain the estimate is.

### Zone Thresholds

Default probability thresholds (configurable):
- Green: ≥ 0.4
- Yellow: ≥ 0.3
- Red: ≥ 0.3 (at least 30% chance you're impaired → protect)

## Configuration

Config stored at `~/.circadia/config.json`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `utc_offset_hours` | 0 | Your timezone offset from UTC |
| `work_start_hour` | 9 | When your workday begins (local time) |
| `work_end_hour` | 18 | When your workday ends (local time) |
| `session_duration_limit_hours` | 8 | Hours before session fatigue maxes out |
| `block_force_push_in_red` | true | Block `git push --force` in red zone |
| `block_deploy_in_red` | true | Block deployments in red zone |
| `fatigue_error_patterns` | [...] | Error patterns to flag in red/yellow zones |

## Shell Integration

Add to your `.bashrc`/`.zshrc` for a persistent zone indicator:

```bash
# Show cognitive zone in your prompt
export PS1='$(circadia status --short) '"$PS1"
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
