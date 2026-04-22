"""Self-profile building from code patterns.

Builds a 'self' corpus representing what is normal for a codebase,
optionally using git history to learn from past commits.
"""

import hashlib
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from .extractor import (
    FeatureVector,
    extract_patterns_from_directory,
    extract_patterns_from_file,
    extract_patterns_from_source,
)


@dataclass
class SelfProfile:
    """Represents the 'self' identity of a codebase."""
    name: str = ""
    root_path: str = ""
    created_at: str = ""
    granularity: str = "function"
    num_files: int = 0
    num_patterns: int = 0

    # Statistical summary of the self corpus
    feature_means: List[float] = field(default_factory=list)
    feature_stds: List[float] = field(default_factory=list)
    feature_mins: List[float] = field(default_factory=list)
    feature_maxs: List[float] = field(default_factory=list)

    # The actual pattern vectors
    patterns: List[FeatureVector] = field(default_factory=list)

    def pattern_vectors(self) -> List[List[float]]:
        """Get pattern vectors as list of float lists."""
        return [p.to_list() for p in self.patterns]

    def compute_statistics(self):
        """Compute mean, std, min, max for each feature dimension."""
        if not self.patterns:
            return

        vectors = self.pattern_vectors()
        n = len(vectors)
        dims = len(vectors[0])

        self.feature_means = []
        self.feature_stds = []
        self.feature_mins = []
        self.feature_maxs = []

        for d in range(dims):
            values = [v[d] for v in vectors]
            mean = sum(values) / n
            variance = sum((v - mean) ** 2 for v in values) / n
            std = variance ** 0.5
            self.feature_means.append(mean)
            self.feature_stds.append(std)
            self.feature_mins.append(min(values))
            self.feature_maxs.append(max(values))

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "root_path": self.root_path,
            "created_at": self.created_at,
            "granularity": self.granularity,
            "num_files": self.num_files,
            "num_patterns": self.num_patterns,
            "feature_means": self.feature_means,
            "feature_stds": self.feature_stds,
            "feature_mins": self.feature_mins,
            "feature_maxs": self.feature_maxs,
            "patterns": [
                {
                    "name": p.name,
                    "source_file": p.source_file,
                    "source_line": p.source_line,
                    "kind": p.kind,
                    "vector": p.to_list(),
                }
                for p in self.patterns
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SelfProfile":
        """Deserialize from dictionary."""
        profile = cls(
            name=data.get("name", ""),
            root_path=data.get("root_path", ""),
            created_at=data.get("created_at", ""),
            granularity=data.get("granularity", "function"),
            num_files=data.get("num_files", 0),
            num_patterns=data.get("num_patterns", 0),
            feature_means=data.get("feature_means", []),
            feature_stds=data.get("feature_stds", []),
            feature_mins=data.get("feature_mins", []),
            feature_maxs=data.get("feature_maxs", []),
        )
        for pdata in data.get("patterns", []):
            vec = FeatureVector.from_list(
                pdata["vector"],
                name=pdata.get("name", ""),
                source_file=pdata.get("source_file", ""),
                source_line=pdata.get("source_line", 0),
                kind=pdata.get("kind", "function"),
            )
            profile.patterns.append(vec)
        return profile

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SelfProfile":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))


def build_profile(source_path: str, granularity: str = "function",
                  history: str = "", name: str = "") -> SelfProfile:
    """Build a self-profile from a source directory.

    Args:
        source_path: Path to source directory
        granularity: Pattern granularity ('function', 'class', 'module')
        history: Git history duration (e.g., '6m' for 6 months)
        name: Profile name (defaults to directory basename)

    Returns:
        SelfProfile instance
    """
    source_path = os.path.abspath(source_path)
    if not name:
        name = os.path.basename(source_path)

    profile = SelfProfile(
        name=name,
        root_path=source_path,
        created_at=datetime.now().isoformat(),
        granularity=granularity,
    )

    if history:
        # Extract patterns from git history
        patterns = _extract_from_git_history(source_path, history, granularity)
        # Also add current state
        current_patterns = extract_patterns_from_directory(source_path, granularity)
        # Deduplicate by name+file
        seen = set()
        for p in patterns + current_patterns:
            key = (p.name, p.source_file, p.kind)
            if key not in seen:
                profile.patterns.append(p)
                seen.add(key)
    else:
        profile.patterns = extract_patterns_from_directory(source_path, granularity)

    # Count files
    profile.num_files = len(set(p.source_file for p in profile.patterns if p.source_file))
    profile.num_patterns = len(profile.patterns)
    profile.compute_statistics()

    return profile


def _extract_from_git_history(source_path: str, history: str,
                               granularity: str) -> List[FeatureVector]:
    """Extract patterns from git history.

    Uses subprocess to call git commands and parse historical versions.
    """
    patterns = []

    # Parse history duration
    since_date = _parse_history_duration(history)
    if not since_date:
        return patterns

    try:
        # Get list of commits since the date
        result = subprocess.run(
            ['git', 'log', '--since', since_date, '--format=%H', '--', source_path],
            capture_output=True, text=True, cwd=source_path, timeout=30
        )
        if result.returncode != 0:
            return patterns

        commits = result.stdout.strip().split('\n')
        commits = [c.strip() for c in commits if c.strip()]

        # Sample commits (don't process all of them for large histories)
        if len(commits) > 20:
            # Take evenly spaced samples
            step = len(commits) // 20
            commits = commits[::step][:20]

        for commit in commits:
            try:
                # Get list of Python files at this commit
                ls_result = subprocess.run(
                    ['git', 'ls-tree', '-r', '--name-only', commit],
                    capture_output=True, text=True, cwd=source_path, timeout=30
                )
                if ls_result.returncode != 0:
                    continue

                py_files = [f for f in ls_result.stdout.strip().split('\n')
                           if f.strip().endswith('.py')]

                # Sample files
                if len(py_files) > 10:
                    step = len(py_files) // 10
                    py_files = py_files[::step][:10]

                for py_file in py_files:
                    try:
                        show_result = subprocess.run(
                            ['git', 'show', f'{commit}:{py_file}'],
                            capture_output=True, text=True, cwd=source_path, timeout=10
                        )
                        if show_result.returncode == 0:
                            file_patterns = extract_patterns_from_source(
                                show_result.stdout,
                                source_file=py_file,
                                granularity=granularity,
                            )
                            patterns.extend(file_patterns)
                    except (subprocess.TimeoutExpired, Exception):
                        continue

            except (subprocess.TimeoutExpired, Exception):
                continue

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass

    return patterns


def _parse_history_duration(history: str) -> Optional[str]:
    """Parse history duration string like '3m', '6m', '1y' to a git --since date.

    Returns a string suitable for `git log --since`.
    """
    if not history:
        return None

    # Git accepts relative dates directly like "6 months ago" or "3 months ago"
    history = history.strip()
    if history.endswith('m'):
        try:
            months = int(history[:-1])
            return f"{months} months ago"
        except ValueError:
            return None
    elif history.endswith('y'):
        try:
            years = int(history[:-1])
            return f"{years} years ago"
        except ValueError:
            return None
    elif history.endswith('d'):
        try:
            days = int(history[:-1])
            return f"{days} days ago"
        except ValueError:
            return None
    # Pass through as-is for formats git understands (must contain a digit)
    if any(c.isdigit() for c in history):
        return history
    return None


def profile_file_summary(profile: SelfProfile) -> str:
    """Generate a human-readable summary of a self-profile."""
    lines = []
    lines.append(f"🧬 Self-Profile: {profile.name}")
    lines.append(f"   Root: {profile.root_path}")
    lines.append(f"   Created: {profile.created_at}")
    lines.append(f"   Granularity: {profile.granularity}")
    lines.append(f"   Files: {profile.num_files}")
    lines.append(f"   Patterns: {profile.num_patterns}")

    if profile.feature_means:
        fn = FeatureVector.feature_names()
        lines.append("")
        lines.append("   Feature Statistics:")
        for i, name in enumerate(fn):
            if i < len(profile.feature_means):
                mean = profile.feature_means[i]
                std = profile.feature_stds[i] if i < len(profile.feature_stds) else 0
                lines.append(f"     {name:30s} μ={mean:.3f} σ={std:.3f}")

    return '\n'.join(lines)
