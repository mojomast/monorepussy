"""Soil layer management — snapshot creation and drift detection."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .db import SoilDB
from .diff import compute_diff, extract_changed_keys
from .hash import file_hash, string_hash


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SoilLayer:
    """Represents a single soil layer (a state snapshot in time)."""

    def __init__(
        self,
        path: str,
        content_hash: str,
        content_text: str,
        timestamp: Optional[datetime] = None,
        diff_text: str = "",
        actor: str = "",
        context: str = "",
        is_drift: bool = False,
        desired_hash: str = "",
        layer_id: Optional[int] = None,
    ):
        self.path = path
        self.content_hash = content_hash
        self.content_text = content_text
        self.timestamp = timestamp or _now()
        self.diff_text = diff_text
        self.actor = actor
        self.context = context
        self.is_drift = is_drift
        self.desired_hash = desired_hash
        self.layer_id = layer_id


class SoilMemory:
    """Manages soil layers — recording snapshots and detecting drift."""

    def __init__(self, db: SoilDB):
        self.db = db

    def snapshot(
        self,
        path: str,
        actor: str = "",
        context: str = "",
    ) -> SoilLayer:
        """Record a new soil layer for a file.

        Reads the current file content, computes hash and diff against
        the previous layer, and stores the result.

        Args:
            path: File path to snapshot.
            actor: Who/what initiated the snapshot.
            context: Additional context.

        Returns:
            The created SoilLayer.

        Raises:
            FileNotFoundError: If the file doesn't exist.
        """
        abs_path = os.path.abspath(path)
        if not os.path.isfile(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")

        content_text = Path(abs_path).read_text(encoding="utf-8", errors="replace")
        c_hash = string_hash(content_text)

        # Get previous layer for diff
        prev = self.db.get_latest_layer(abs_path)
        diff_text = ""
        is_drift = False
        desired_hash = ""

        # Check against explicit desired state first
        desired = self.db.get_desired_state(abs_path)
        if desired:
            desired_hash = desired["desired_hash"]
            is_drift = c_hash != desired_hash
        elif prev:
            # No explicit desired state — first snapshot is the baseline
            if prev["content_hash"] != c_hash:
                is_drift = True
            desired_hash = prev.get("desired_hash", "")

        # Compute diff from previous layer if content changed
        if prev and prev["content_hash"] != c_hash:
            diff_text = compute_diff(prev["content_text"], content_text)

        layer_id = self.db.add_layer(
            path=abs_path,
            content_hash=c_hash,
            content_text=content_text,
            diff_text=diff_text,
            actor=actor,
            context=context,
            is_drift=is_drift,
            desired_hash=desired_hash,
        )

        return SoilLayer(
            path=abs_path,
            content_hash=c_hash,
            content_text=content_text,
            diff_text=diff_text,
            actor=actor,
            context=context,
            is_drift=is_drift,
            desired_hash=desired_hash,
            layer_id=layer_id,
        )

    def snapshot_text(
        self,
        path: str,
        content_text: str,
        actor: str = "",
        context: str = "",
        desired_hash: str = "",
    ) -> SoilLayer:
        """Record a soil layer from explicit text content (no file read).

        Useful for testing and programmatic use.

        Args:
            path: Logical path for the content.
            content_text: The content text.
            actor: Who/what initiated the snapshot.
            context: Additional context.
            desired_hash: Hash of desired state.

        Returns:
            The created SoilLayer.
        """
        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
        c_hash = string_hash(content_text)

        prev = self.db.get_latest_layer(abs_path)
        diff_text = ""
        is_drift = False

        if prev:
            if prev["content_hash"] != c_hash:
                diff_text = compute_diff(prev["content_text"], content_text)
                is_drift = True
            if not desired_hash:
                desired_hash = prev.get("desired_hash", "")

        # Check desired state
        desired = self.db.get_desired_state(abs_path)
        if desired:
            if not desired_hash:
                desired_hash = desired["desired_hash"]
            if c_hash != desired_hash:
                is_drift = True

        layer_id = self.db.add_layer(
            path=abs_path,
            content_hash=c_hash,
            content_text=content_text,
            diff_text=diff_text,
            actor=actor,
            context=context,
            is_drift=is_drift,
            desired_hash=desired_hash,
        )

        return SoilLayer(
            path=abs_path,
            content_hash=c_hash,
            content_text=content_text,
            diff_text=diff_text,
            actor=actor,
            context=context,
            is_drift=is_drift,
            desired_hash=desired_hash,
            layer_id=layer_id,
        )

    def detect_drift(self, path: str) -> Optional[Dict]:
        """Detect drift for a file by comparing current state with desired state.

        Args:
            path: File path to check.

        Returns:
            Drift info dict if drift detected, None otherwise.
        """
        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path

        # Get current file content
        if os.path.isfile(abs_path):
            current_text = Path(abs_path).read_text(encoding="utf-8", errors="replace")
            current_hash = string_hash(current_text)
        else:
            latest = self.db.get_latest_layer(abs_path)
            if latest:
                current_text = latest["content_text"]
                current_hash = latest["content_hash"]
            else:
                return None

        desired = self.db.get_desired_state(abs_path)
        if not desired:
            # Compare against latest known non-drift state
            layers = self.db.get_layers(abs_path, depth=50)
            for layer in layers:
                if not layer["is_drift"]:
                    return {
                        "path": abs_path,
                        "current_hash": current_hash,
                        "desired_hash": layer["content_hash"],
                        "is_drift": current_hash != layer["content_hash"],
                        "changed_keys": extract_changed_keys(
                            layer["content_text"], current_text
                        ) if current_hash != layer["content_hash"] else [],
                    }
            return None

        is_drift = current_hash != desired["desired_hash"]
        if not is_drift:
            return None

        changed_keys = extract_changed_keys(desired.get("desired_text", ""), current_text)

        return {
            "path": abs_path,
            "current_hash": current_hash,
            "desired_hash": desired["desired_hash"],
            "is_drift": True,
            "changed_keys": changed_keys,
        }

    def get_drift_history(self, path: str, depth: int = 10) -> List[Dict]:
        """Get the drift history for a path.

        Args:
            path: File path.
            depth: Maximum number of layers.

        Returns:
            List of layer dicts.
        """
        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
        return self.db.get_layers(abs_path, depth)

    def detect_correction(self, path: str) -> Optional[Dict]:
        """Detect when 'drift' is actually a correction — i.e., the desired
        state keeps getting overridden to the same value.

        This is the killer feature: detect when a config keeps drifting back
        to the same 'wrong' value because the desired state is itself wrong.

        Args:
            path: File path to analyze.

        Returns:
            Correction analysis dict if pattern detected, None otherwise.
        """
        abs_path = os.path.abspath(path) if not os.path.isabs(path) else path
        layers = self.db.get_layers(abs_path, depth=50)

        if len(layers) < 3:
            return None

        # Collect drift hashes (content hashes that were marked as drift)
        drift_hashes = [l["content_hash"] for l in layers if l["is_drift"]]
        non_drift_hashes = [l["content_hash"] for l in layers if not l["is_drift"]]

        if not drift_hashes or not non_drift_hashes:
            return None

        # Find the most common drift hash
        from collections import Counter
        drift_counter = Counter(drift_hashes)
        most_common_hash, most_common_count = drift_counter.most_common(1)[0]

        # If the same drift value appears multiple times, it might be a correction
        if most_common_count < 2:
            return None

        # Check if the non-drift (desired) values are different from this drift
        desired_hashes = set(non_drift_hashes)
        if most_common_hash in desired_hashes:
            return None

        # Find the key changes in the drift
        drift_layers = [l for l in layers if l["is_drift"] and l["content_hash"] == most_common_hash]
        if drift_layers:
            prev_layers = [l for l in layers if not l["is_drift"]]
            if prev_layers:
                changed_keys = extract_changed_keys(
                    prev_layers[0]["content_text"], drift_layers[0]["content_text"]
                )
            else:
                changed_keys = []
        else:
            changed_keys = []

        return {
            "path": abs_path,
            "recurring_hash": most_common_hash,
            "recurrence_count": most_common_count,
            "total_drifts": len(drift_hashes),
            "diagnosis": "DRIFT_IS_CORRECTION",
            "message": (
                f"The same drift value has appeared {most_common_count} times. "
                f"The desired state may be wrong."
            ),
            "changed_keys": changed_keys,
            "suggestion": (
                f"Update desired state to match the recurring drift value "
                f"(hash: {most_common_hash[:12]}...)"
            ),
        }
