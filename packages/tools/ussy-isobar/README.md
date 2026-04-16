# Isobar — Meteorological Micro-Climate Analysis for Developer Workspaces

Isobar treats your codebase like a weather system. It maps git history and AST dependency analysis to meteorological concepts — temperature measures change velocity, pressure measures dependency load, humidity measures bug density, and fronts mark instability boundaries between volatile and stable modules.

## Quick Start

```bash
# Install
pip install -e .

# Survey your codebase's atmospheric conditions
isobar survey --path /path/to/repo

# See current weather conditions
isobar current --path /path/to/repo

# Generate a synoptic weather map
isobar map --path /path/to/repo

# Detect active fronts (instability boundaries)
isobar fronts --path /path/to/repo

# Get a weather forecast
isobar forecast --path /path/to/repo --ahead 5

# Check for storm warnings
isobar warn --path /path/to/repo --threshold warning

# Analyze a specific file's micro-climate
isobar climate --path /path/to/repo auth.py

# View historical weather patterns
isobar history --path /path/to/repo --last-month
```

## How It Works

### Meteorological Mapping

| Meteorological Concept | Codebase Analog | Computation |
|----------------------|-----------------|-------------|
| **Temperature** | Change velocity | Commits per week per file (°C = weekly commit rate × 10) |
| **Pressure** | Dependency load | Number of files that import this file (mb = import count × 5) |
| **Humidity** | Bug density | Ratio of bug-fix commits to total commits (%rh) |
| **Fronts** | Instability boundaries | Boundaries between hot (volatile) and cold (stable) modules |
| **Cyclones** | Destructive change patterns | Files with high temperature + high pressure + high humidity |
| **Anticyclones** | Protected stable zones | Files with low temperature + low humidity despite high pressure |

### Frontogenesis Detection

Isobar detects fronts using the meteorological frontogenesis condition: when the gradient between volatile and stable code is *sharpening* over time. Warm fronts form where hot code is advancing into stable territory (dependency pressure building). Cold fronts form where stable code is being encroached by volatility.

### Cyclone Classification

Cyclones are rated on the Saffir-Simpson scale:
- **Tropical Depression**: Temperature > 40°C, single dependent
- **Tropical Storm**: Temperature > 50°C, multiple dependents
- **Category 1-5**: Escalating thresholds for temperature × pressure × humidity

## Architecture

```
isobar/
├── scanner.py     # GitScanner — parses git log into FileHistory/ScanResult
├── fields.py      # AtmosphericField — computes temperature, pressure, humidity
├── fronts.py      # Front detection and classification
├── cyclones.py    # Cyclone/anticyclone detection and storm warnings
├── forecast.py    # Trend-based weather forecasting
├── synoptic.py    # ASCII synoptic map and current conditions rendering
├── history.py     # Historical weather analysis and sprint comparison
├── cli.py         # CLI interface with 8 subcommands
├── __init__.py    # Package metadata
└── __main__.py    # python -m isobar support
```

### Data Flow

```
GitScanner.scan()
    → ScanResult (file_histories, import_graph)
        → compute_fields()
            → AtmosphericField (profiles, hot/cold/high-pressure/cyclonic files)
                → detect_fronts()
                → detect_cyclones()
                → generate_forecast()
                → render_synoptic_map()
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `survey` | Scan git history and compute atmospheric fields |
| `current` | Show current conditions summary |
| `map` | Display ASCII synoptic weather map |
| `fronts` | Detect and classify active fronts |
| `forecast` | Weather forecast for next N sprints |
| `warn` | Current storm warnings |
| `climate` | Micro-climate analysis for a specific file |
| `history` | Historical weather patterns |

## Output Formats

The `map` and `survey` commands support `--format json` for machine-readable output. All other commands produce formatted ASCII text.

## Installation

```bash
git clone https://github.com/mojomast/isobarussy.git
cd isobarussy
pip install -e .
```

No external dependencies — pure Python stdlib.

## License

MIT
