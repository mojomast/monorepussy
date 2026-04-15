# Plan9-WebPlumb

A modernized **Plan 9 Plumb server for the browser** — bridging web content to your local machine with Unix-style composability.

## Overview

Plan 9's `plumb` let you send data to the right handler based on content type — click a file path, it opens in your editor; click a URL, it opens in your browser. **Plan9-WebPlumb** brings this philosophy to the browser:

- A **local WebSocket server** (the "Plumber") receives data from a browser extension
- A **browser extension** pipes selected text, URLs, and DOM elements to the server
- A **registry of local handlers** (shell scripts, apps) fires based on regex pattern matching
- The active tab/clipboard is treated as a dynamic filesystem concept (`/mnt/plumb/web`)

**Success demo**: Highlight a GitHub Issue URL in the browser → your local `todo` tool automatically ingests it without a single click.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Browser (Chrome)                      │
│  ┌─────────────────┐    ┌──────────────────────────────┐ │
│  │  Content Script  │───▶│  Background Service Worker   │ │
│  │  (selection,     │    │  (context menus, icon click) │ │
│  │   URL capture)   │    └──────────┬───────────────────┘ │
│  └─────────────────┘               │                     │
│                                     │ WebSocket           │
└─────────────────────────────────────┼─────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────┐
│               Plumber (WebSocket Server)                  │
│                 ws://localhost:31151                       │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐ │
│  │  Message      │   │  Rule Engine  │   │  Dispatch    │ │
│  │  Parser       │──▶│  (regex match)│──▶│  (exec/pipe) │ │
│  └──────────────┘   └──────────────┘   └──────┬───────┘ │
│                                                │          │
└────────────────────────────────────────────────┼──────────┘
                                                 │
                    ┌──────────────┐   ┌─────────▼────────┐
                    │  todo script │   │  custom handler   │
                    │  (example)   │   │  (your scripts)   │
                    └──────────────┘   └──────────────────┘
```

## Installation

```bash
pip install plan9webplumb
```

For development:

```bash
git clone https://github.com/your-org/plan9webplumb.git
cd plan9webplumb
pip install -e ".[dev]"
```

## Usage

### Starting the Plumber Server

```bash
plan9webplumb serve
plan9webplumb serve --host 0.0.0.0 --port 31151
```

### Managing Handlers

```bash
# List all handlers and rules
plan9webplumb handlers list

# Add a handler with a pattern rule
plan9webplumb handlers add \
  --name todo \
  --command "echo '{data}' >> ~/todo.md" \
  --pattern "https://github\\.com/[^/]+/[^/]+/issues/\\d+" \
  --msg-type url

# Test which handlers would fire for a URL
plan9webplumb handlers test --url "https://github.com/nous-research/plan9webplumb/issues/42"

# Remove a handler
plan9webplumb handlers remove todo
```

### Checking Status

```bash
plan9webplumb status
```

### Browser Extension

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" → select the `browser_extension/` directory
4. Right-click selected text → "Plumb selection"
5. Or right-click a link → "Plumb link"

### Running as a Module

```bash
python -m plan9webplumb serve
```

## Configuration

Configuration is stored in `~/.config/plan9webplumb/` (respects `$XDG_CONFIG_HOME`):

```
~/.config/plan9webplumb/
├── config.yaml          # Server settings (host, port)
├── handlers/            # Handler definitions (YAML)
│   └── todo.yaml
└── rules/               # Pattern-matching rules (YAML)
    └── github_issue_rule.yaml
```

### Handler Definition

```yaml
name: todo
command: "echo '{data}' >> ~/todo.md"
action: exec
description: "Ingest GitHub Issue URLs into local todo list"
timeout: 30.0
enabled: true
```

### Rule Definition

```yaml
name: github_issue_rule
pattern: "https://github\\.com/[^/]+/[^/]+/issues/\\d+"
handler: todo
msg_type: url
priority: 10
enabled: true
```

### Command Substitution

Handler commands support these placeholders:
- `{data}` — The message data (selected text, etc.)
- `{url}` — The source URL
- `{title}` — The page title
- `{src}` — The message source (e.g., "browser")
- `{type}` — The message type (text, url, dom_element, clipboard)

## The /mnt/plumb/web Concept

Inspired by Plan 9's filesystem metaphor, Plan9-WebPlumb treats the browser as a writable data source. The plumber server acts as `/mnt/plumb/web` — a dynamic endpoint where browser data flows in and local handlers respond.

## License

MIT
