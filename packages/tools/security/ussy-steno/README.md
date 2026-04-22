# Stenography — Steganographic Code Review Tool

**Detect invisible attacks hiding in your source code.**

[![CI](https://github.com/mojomast/stenographussy/actions/workflows/ci.yml/badge.svg)](https://github.com/mojomast/stenographussy/actions/workflows/ci.yml)

Code review is a security blind spot for steganographic attacks. Malicious actors can hide backdoors using techniques invisible to standard diff views — zero-width characters, Unicode homoglyphs, RTL overrides, whitespace encoding, and comment steganography. **Stenography** detects them all.

## 🚨 What It Detects

| Attack Type | Example | Risk |
|---|---|---|
| **Zero-width characters** | `password​ = "secret"` (ZWSP U+200B) | CRITICAL — changes string equality |
| **Homoglyph substitution** | `pаssword` (Cyrillic а vs Latin a) | CRITICAL — lookalike identifiers |
| **RTL override exploits** | `"user‮"nimda"` (U+202E Trojan Source) | CRITICAL — reverses displayed text |
| **Whitespace steganography** | Trailing spaces encoding binary data | HIGH — hidden data in whitespace |
| **Comment steganography** | Variation selectors encoding payloads | MEDIUM — invisible data in comments |

## 📦 Installation

```bash
pip install -e .
```

Or install from the repository:

```bash
git clone https://github.com/mojomast/stenographussy.git
cd stenographussy
pip install -e .
```

**Zero external dependencies** — uses only Python standard library for core scanning.

## 🚀 Quick Start

```bash
# Scan a directory
stenography scan ./src

# Scan a git diff (only changed lines)
stenography diff HEAD~1

# Output as JSON
stenography scan --format json ./src

# Output as SARIF (for GitHub Code Scanning)
stenography scan --format sarif ./src

# Scan from stdin
cat suspicious.py | stenography scan -

# Adjust whitespace entropy threshold
stenography scan --entropy-threshold 0.5 ./src

# Disable colored output
stenography scan --no-color ./src
```

## 🔍 Scanner Details

### 1. Zero-Width Character Scanner (`STEN001`)

Detects all zero-width and invisible Unicode characters in source files. These characters are completely invisible in editors and diff views but change how code executes.

**Detects 30+ characters including:**
- ZWSP (U+200B) — Zero Width Space
- ZWNJ (U+200C) — Zero Width Non-Joiner
- ZWJ (U+200D) — Zero Width Joiner
- LRM (U+200E) — Left-to-Right Mark
- RLM (U+200F) — Right-to-Left Mark
- WJ (U+2060) — Word Joiner
- FA (U+2061) — Function Application
- IT (U+2062) — Invisible Times
- IS (U+2063) — Invisible Separator
- IP (U+2064) — Invisible Plus
- ZWNBSP (U+FEFF) — Zero Width No-Break Space / BOM
- Variation Selectors (U+FE00–U+FE0F)
- And many more...

**Example attack:**
```python
password​ = "secret"  # Has invisible ZWSP after 'password'
# password != "password\u200b" → different identifier!
```

### 2. Homoglyph Detector (`STEN002`)

Scans identifiers and string literals for mixed-script characters that look identical but have different Unicode codepoints. Uses 50+ known homoglyph pairs across Cyrillic, Greek, Latin, and fullwidth character sets.

**Detects:**
- Cyrillic/Latin confusables (а↔a, е↔e, о↔o, р↔p, с↔c, etc.)
- Greek/Latin confusables (Α↔A, Β↔B, Ο↔O, etc.)
- Lookalike digits (0/O, 1/l/I)
- Fullwidth variants (ａ↔a, Ａ↔A, etc.)
- Mixed-script identifiers (CRITICAL)

**Example attack:**
```python
pаssword = "hacked"  # Cyrillic а (U+0430) instead of Latin a
# Visually identical, but completely different identifier!
```

### 3. RTL/Formatting Exploit Scanner (`STEN003`)

Detects right-to-left overrides, bidi controls, and invisible formatting characters that change how code renders vs executes. This covers the **Trojan Source** class of attacks.

**Detects:**
- U+202A–U+202E: Bidi embedding/override controls
- U+2066–U+2069: Bidi isolate controls
- Soft hyphens (U+00AD)
- Non-breaking spaces (U+00A0)
- Arabic Letter Mark (U+061C)

**Example attack (Trojan Source):**
```python
if access_level != "user‮":  # RLO reverses displayed text
    grant_admin()             # Condition always true!
```

### 4. Whitespace Steganography Detector (`STEN004`)

Analyzes whitespace patterns for encoded data using entropy analysis.

**Detects:**
- Tab/space binary encoding (spaces=0, tabs=1) — classic steganographic technique
- Trailing whitespace patterns that encode data
- Mixed tab/space indentation anomalies (potential encoding)
- Shannon entropy analysis with configurable threshold

**Example attack:**
```
x = 1    	  	# Trailing spaces/tabs encode "HI" in binary
```

### 5. Comment Steganography Scanner (`STEN005`)

Checks comments and string literals for hidden data using Unicode steganography.

**Detects:**
- Variation selectors (U+FE00–U+FE0F) — can encode ~16 bits per character
- Combining characters that stack invisibly (3+ consecutive = HIGH)
- Modifier letters (U+02B0–U+02FF)
- Superscript/subscript characters
- Unicode tag characters (U+E0000–U+E007F) — completely invisible, can encode arbitrary text

## 📊 Risk Scoring

Context-aware severity based on where the finding appears:

| Context | Severity | Rationale |
|---|---|---|
| **In identifier** | CRITICAL | Changes code execution path |
| **In string literal** | HIGH | Could bypass string comparisons |
| **In comment** | MEDIUM | May contain hidden instructions |
| **In whitespace** | LOW + entropy check | Only dangerous if encoding data |

## 📋 Output Formats

### Table (default)
```
  ╔══════════════════════════════════════════════╗
  ║          STENOGRAPHY — Scan Results          ║
  ║     Steganographic Code Review Tool          ║
  ╚══════════════════════════════════════════════╝

  Findings: CRITICAL:3 | HIGH:2 | MEDIUM:1

  SEVERITY   SCANNER        FILE                           LINE  COL  MESSAGE
  ────────── ────────────── ────────────────────────────── ───── ──── ──────────────────────────────────────
  CRITICAL   zero_width     test.py                           1    9  Zero-width character detected: ZWSP
  CRITICAL   homoglyph      test.py                           5    2  Homoglyph detected: Cyrillic а
  HIGH       rtl            test.py                           3    6  RTL/formatting exploit: RLO
```

### JSON
```bash
stenography scan --format json ./src
```

### SARIF
For integration with GitHub Code Scanning, Azure DevOps, and other SARIF-compatible tools:
```bash
stenography scan --format sarif ./src > results.sarif
```

## 🔧 CLI Reference

```
stenography scan [OPTIONS] PATH [PATH...]
stenography diff [OPTIONS] REF

Commands:
  scan    Scan files/directories for steganographic content
  diff    Scan only changed lines in a git diff

Scan Options:
  PATH                  File or directory paths (use '-' for stdin)
  --format, -f          Output format: table, json, sarif (default: table)
  --entropy-threshold   Whitespace entropy threshold 0-1 (default: 0.8)
  --no-color            Disable colored output

Diff Options:
  REF                   Git diff reference (e.g., HEAD~1, main..feature)
  --format, -f          Output format: table, json, sarif (default: table)
  --entropy-threshold   Whitespace entropy threshold 0-1 (default: 0.8)

Exit Codes:
  0  No findings (clean)
  1  Findings detected
```

## 🧪 Running Tests

```bash
pip install pytest
pytest tests/ -v
```

Test fixtures in `tests/fixtures/` contain actual steganographic content to validate all scanners.

## 🏗️ Architecture

```
Input Layer (Git Diff / File Tree / Stdin)
    ↓
Unicode Normalization (NFD decomposition for analysis)
    ↓
Detection Pipeline (5 scanners run in parallel)
    ├─ Zero-Width Character Scanner
    ├─ Homoglyph Detector
    ├─ RTL/Formatting Exploit Scanner
    ├─ Whitespace Steganography Detector
    └─ Comment Steganography Scanner
    ↓
Risk Scoring Engine (context-aware severity)
    ↓
Output Formatter (Table / JSON / SARIF)
```

## ⚠️ Disclaimer

This tool is for defensive security purposes. The steganographic techniques described are well-known attack vectors. Use Stenography to **detect** these attacks in your codebase, not to plant them.

## 📄 License

MIT
