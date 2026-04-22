"""Scanner — directory scan and JSON ingestion for CI pipeline artifacts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ussy_coroner.models import PipelineRun, Stage, StageStatus


# Patterns that indicate a stage failure
_FAILURE_PATTERNS = [
    re.compile(r"FAILED", re.IGNORECASE),
    re.compile(r"ERROR", re.IGNORECASE),
    re.compile(r"FATAL", re.IGNORECASE),
    re.compile(r"exception", re.IGNORECASE),
    re.compile(r"segmentation fault", re.IGNORECASE),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"exit code [1-9]", re.IGNORECASE),
]

# Patterns for success
_SUCCESS_PATTERNS = [
    re.compile(r"BUILD SUCCESSFUL", re.IGNORECASE),
    re.compile(r"passed", re.IGNORECASE),
    re.compile(r"all tests passed", re.IGNORECASE),
    re.compile(r"exit code 0", re.IGNORECASE),
]


def _detect_status(log_content: str) -> StageStatus:
    """Detect stage status from log content."""
    has_failure = any(p.search(log_content) for p in _FAILURE_PATTERNS)
    has_success = any(p.search(log_content) for p in _SUCCESS_PATTERNS)
    if has_failure and not has_success:
        return StageStatus.FAILURE
    if has_success and not has_failure:
        return StageStatus.SUCCESS
    if has_failure and has_success:
        # If both, assume failure (failure lines typically override)
        return StageStatus.FAILURE
    return StageStatus.SUCCESS


def _extract_env_vars(log_content: str) -> dict[str, str]:
    """Extract environment variable declarations from log content."""
    env_vars: dict[str, str] = {}
    # Match patterns like: export VAR=value, VAR=value, set VAR=value
    for m in re.finditer(r'(?:export\s+|set\s+)?([A-Z_][A-Z0-9_]*)=(\S+)', log_content):
        env_vars[m.group(1)] = m.group(2)
    return env_vars


def _compute_file_hash(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except (OSError, IOError):
        return ""
    return h.hexdigest()


def scan_directory(directory: str | Path) -> PipelineRun:
    """Scan a directory for CI pipeline run artifacts.

    Expected directory layout:
      run.json or pipeline.json  — run metadata
      stage_<name>.log           — stage log files
      env_dump.json              — environment variable dumps
      artifacts/                 — artifact directory
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Directory not found: {directory}")

    # Load run metadata
    run_id = directory.name
    metadata: dict[str, Any] = {}
    for meta_file in ["run.json", "pipeline.json"]:
        meta_path = directory / meta_file
        if meta_path.exists():
            with open(meta_path) as f:
                data = json.load(f)
            run_id = data.get("run_id", run_id)
            metadata = data.get("metadata", data)
            break

    run = PipelineRun(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc),
        metadata=metadata,
    )

    # Load env dump if present
    global_env: dict[str, str] = {}
    env_path = directory / "env_dump.json"
    if env_path.exists():
        with open(env_path) as f:
            global_env = json.load(f)

    # Scan for stage log files
    stage_files = sorted(directory.glob("stage_*.log"))
    for idx, log_path in enumerate(stage_files):
        # Extract stage name from filename: stage_checkout.log -> checkout
        stage_name = log_path.stem.replace("stage_", "")
        log_content = log_path.read_text(errors="replace")
        status = _detect_status(log_content)
        env_vars = {**global_env, **_extract_env_vars(log_content)}

        # Compute artifact hashes
        artifact_hashes: dict[str, str] = {}
        artifacts: list[str] = []

        # Check for artifacts directory specific to this stage
        artifact_dir = directory / f"artifacts_{stage_name}"
        if artifact_dir.is_dir():
            for art_file in artifact_dir.rglob("*"):
                if art_file.is_file():
                    rel = str(art_file.relative_to(artifact_dir))
                    artifacts.append(rel)
                    artifact_hashes[rel] = _compute_file_hash(art_file)

        # Also check general artifacts directory
        general_art_dir = directory / "artifacts"
        if general_art_dir.is_dir():
            for art_file in general_art_dir.rglob("*"):
                if art_file.is_file():
                    rel = str(art_file.relative_to(general_art_dir))
                    if rel not in artifact_hashes:
                        artifacts.append(rel)
                        artifact_hashes[rel] = _compute_file_hash(art_file)

        stage = Stage(
            name=stage_name,
            index=idx,
            status=status,
            log_content=log_content,
            env_vars=env_vars,
            artifacts=artifacts,
            artifact_hashes=artifact_hashes,
        )
        run.stages.append(stage)

    return run


def ingest_json(data: dict[str, Any] | str | Path) -> PipelineRun:
    """Ingest pipeline run data from a JSON dict or file path."""
    if isinstance(data, (str, Path)):
        path = Path(data)
        with open(path) as f:
            data = json.load(f)

    run_id = data.get("run_id", "unknown")
    stages_data = data.get("stages", [])

    run = PipelineRun(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc),
        metadata=data.get("metadata", {}),
    )

    for idx, sd in enumerate(stages_data):
        status_str = sd.get("status", "success")
        try:
            status = StageStatus(status_str)
        except ValueError:
            status = StageStatus.SUCCESS

        log_content = sd.get("log_content", sd.get("log", ""))
        if status == StageStatus.SUCCESS and log_content:
            status = _detect_status(log_content)

        env_vars = sd.get("env_vars", sd.get("env", {}))
        artifacts = sd.get("artifacts", [])
        artifact_hashes = sd.get("artifact_hashes", {})

        stage = Stage(
            name=sd.get("name", f"stage_{idx}"),
            index=sd.get("index", idx),
            status=status,
            log_content=log_content,
            env_vars=env_vars if isinstance(env_vars, dict) else {},
            artifacts=artifacts if isinstance(artifacts, list) else [],
            artifact_hashes=artifact_hashes if isinstance(artifact_hashes, dict) else {},
        )
        run.stages.append(stage)

    return run
