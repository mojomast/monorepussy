"""Git hooks for Circadia — risky operation gating based on cognitive zone."""

from __future__ import annotations

import os
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

from ussy_circadia.zones import CognitiveZone
from ussy_circadia.config import CircadiaConfig, GitHooksConfig
from ussy_circadia.estimator import CircadianEstimator
from ussy_circadia.session import SessionTracker


# Git hook script templates
PRE_PUSH_HOOK = """#!/usr/bin/env python3
\"\"\"Circadia pre-push hook — gates risky git operations based on cognitive zone.\"\"\"

import sys
import subprocess

def get_zone():
    result = subprocess.run(
        [sys.executable, "-m", "circadia", "status", "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return "green"  # Default to permissive on error
    try:
        import json
        data = json.loads(result.stdout)
        return data.get("zone", "green")
    except (json.JSONDecodeError, KeyError):
        return "green"

def is_force_push():
    # Check if any --force flag is in the push command
    for arg in sys.argv[1:]:
        if "--force" in arg or "-f" == arg:
            return True
    return False

def main():
    zone = get_zone()
    
    if is_force_push():
        if zone == "red":
            print("🔴 CIRCADIA BLOCKED: Force push blocked in RED zone.")
            print("   Override with: git push --force --i-know-its-red-zone")
            # Check for override
            for arg in sys.argv[1:]:
                if "--i-know-its-red-zone" in arg:
                    print("   ⚠️  Override accepted. Proceeding with force push.")
                    sys.exit(0)
            sys.exit(1)
        elif zone == "yellow":
            print("🟡 CIRCADIA WARNING: Force push in YELLOW zone requires confirmation.")
            # In a real hook, this would require typed confirmation.
            # For now, allow but warn.
            print("   Consider reviewing your changes before forcing.")

    if zone == "red":
        print("🔴 CIRCADIA: You're in the RED zone. Be careful with this push.")

    sys.exit(0)

if __name__ == "__main__":
    main()
"""

PRE_COMMIT_HOOK = """#!/usr/bin/env python3
\"\"\"Circadia pre-commit hook — adds safeguards during low-performance zones.\"\"\"

import sys
import subprocess

def get_zone():
    result = subprocess.run(
        [sys.executable, "-m", "circadia", "status", "--json"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return "green"
    try:
        import json
        data = json.loads(result.stdout)
        return data.get("zone", "green")
    except (json.JSONDecodeError, KeyError):
        return "green"

def main():
    zone = get_zone()
    
    if zone == "red":
        print("🔴 CIRCADIA: Committing in RED zone.")
        print("   Consider running tests before committing.")
        print("   Fatigue increases defect injection rate 2-3x.")

    sys.exit(0)

if __name__ == "__main__":
    main()
"""


@dataclass
class HookCheckResult:
    """Result of a hook check — whether an operation is allowed."""

    allowed: bool
    zone: CognitiveZone
    message: str = ""
    requires_override: bool = False
    override_flag: str = ""


class GitHooksManager:
    """Manages git hooks for Circadia — installs, removes, and checks hooks."""

    RISKY_OPERATIONS = {
        "force_push",
        "hard_reset",
        "delete_branch",
        "deploy_production",
    }

    def __init__(
        self,
        config: Optional[CircadiaConfig] = None,
        estimator: Optional[CircadianEstimator] = None,
        session_tracker: Optional[SessionTracker] = None,
        repo_path: Optional[str] = None,
    ) -> None:
        """Initialize git hooks manager.

        Args:
            config: Circadia configuration.
            estimator: Circadian state estimator.
            session_tracker: Session tracker for duration.
            repo_path: Path to git repository. Defaults to current directory.
        """
        self.config = config or CircadiaConfig()
        self.estimator = estimator or CircadianEstimator(
            utc_offset_hours=self.config.utc_offset_hours
        )
        self.session_tracker = session_tracker or SessionTracker()
        self.repo_path = Path(repo_path or os.getcwd())

    @property
    def hooks_dir(self) -> Path:
        """Path to the git hooks directory."""
        return self.repo_path / ".git" / "hooks"

    def _hook_path(self, hook_name: str) -> Path:
        """Get the path for a specific hook file."""
        return self.hooks_dir / hook_name

    def is_git_repo(self) -> bool:
        """Check if the current directory is a git repository."""
        return (self.repo_path / ".git").exists()

    def is_installed(self, hook_name: str) -> bool:
        """Check if a specific Circadia hook is installed.

        Args:
            hook_name: Name of the hook (e.g., 'pre-push', 'pre-commit').

        Returns:
            True if the hook file exists and contains Circadia markers.
        """
        hook_path = self._hook_path(hook_name)
        if not hook_path.exists():
            return False
        try:
            content = hook_path.read_text()
            return "circadia" in content.lower() or "CIRCADIA" in content
        except OSError:
            return False

    def install_hook(self, hook_name: str, hook_content: str) -> bool:
        """Install a git hook.

        Args:
            hook_name: Name of the hook (e.g., 'pre-push').
            hook_content: Content of the hook script.

        Returns:
            True if installation succeeded.

        Raises:
            RuntimeError: If not in a git repo.
        """
        if not self.is_git_repo():
            raise RuntimeError(
                f"Not a git repository: {self.repo_path}"
            )

        self.hooks_dir.mkdir(parents=True, exist_ok=True)
        hook_path = self._hook_path(hook_name)

        hook_path.write_text(hook_content)
        # Make executable
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
        return True

    def install_all(self) -> List[str]:
        """Install all Circadia git hooks.

        Returns:
            List of installed hook names.

        Raises:
            RuntimeError: If not in a git repo.
        """
        hooks = {
            "pre-push": PRE_PUSH_HOOK,
            "pre-commit": PRE_COMMIT_HOOK,
        }
        installed = []
        for name, content in hooks.items():
            self.install_hook(name, content)
            installed.append(name)
        return installed

    def remove_hook(self, hook_name: str) -> bool:
        """Remove a Circadia git hook.

        Args:
            hook_name: Name of the hook to remove.

        Returns:
            True if the hook was removed, False if it didn't exist.
        """
        hook_path = self._hook_path(hook_name)
        if hook_path.exists():
            hook_path.unlink()
            return True
        return False

    def remove_all(self) -> List[str]:
        """Remove all Circadia git hooks.

        Returns:
            List of removed hook names.
        """
        removed = []
        for name in ["pre-push", "pre-commit"]:
            if self.remove_hook(name):
                removed.append(name)
        return removed

    def check_operation(
        self, operation: str, override: bool = False
    ) -> HookCheckResult:
        """Check if a git operation is allowed in the current zone.

        Args:
            operation: Name of the operation (e.g., 'force_push', 'deploy_production').
            override: Whether the user has provided an explicit override flag.

        Returns:
            HookCheckResult indicating whether the operation is allowed.
        """
        from datetime import datetime, timezone

        session_hours = self.session_tracker.get_current_duration_hours()
        zone = self.estimator.current_zone(
            dt=datetime.now(timezone.utc),
            session_hours=session_hours,
        )
        gh = self.config.git_hooks

        if operation == "force_push":
            if zone == CognitiveZone.RED:
                if gh.block_force_push_in_red and not override:
                    return HookCheckResult(
                        allowed=False,
                        zone=zone,
                        message="Force push BLOCKED in RED zone. Use --i-know-its-red-zone to override.",
                        requires_override=True,
                        override_flag="--i-know-its-red-zone",
                    )
                elif gh.block_force_push_in_red and override:
                    return HookCheckResult(
                        allowed=True,
                        zone=zone,
                        message="⚠️ Force push override accepted in RED zone.",
                    )
            elif zone == CognitiveZone.YELLOW:
                if gh.block_force_push_in_yellow:
                    return HookCheckResult(
                        allowed=True,
                        zone=zone,
                        message="⚠️ Force push WARNING in YELLOW zone. Consider reviewing.",
                        requires_override=False,
                    )

        elif operation == "hard_reset":
            if zone == CognitiveZone.RED and gh.block_hard_reset_in_red and not override:
                return HookCheckResult(
                    allowed=False,
                    zone=zone,
                    message="Hard reset BLOCKED in RED zone. Use --i-know-its-red-zone to override.",
                    requires_override=True,
                    override_flag="--i-know-its-red-zone",
                )

        elif operation == "delete_branch":
            if zone == CognitiveZone.RED and gh.block_delete_branch_in_red and not override:
                return HookCheckResult(
                    allowed=False,
                    zone=zone,
                    message="Branch deletion BLOCKED in RED zone. Use --i-know-its-red-zone to override.",
                    requires_override=True,
                    override_flag="--i-know-its-red-zone",
                )

        elif operation == "deploy_production":
            if zone == CognitiveZone.RED and gh.block_deploy_in_red and not override:
                return HookCheckResult(
                    allowed=False,
                    zone=zone,
                    message="Production deploy BLOCKED in RED zone. Use --i-know-its-red-zone to override.",
                    requires_override=True,
                    override_flag="--i-know-its-red-zone",
                )

        # Default: allowed
        return HookCheckResult(
            allowed=True,
            zone=zone,
            message=f"Operation '{operation}' allowed in {zone.value.upper()} zone.",
        )
