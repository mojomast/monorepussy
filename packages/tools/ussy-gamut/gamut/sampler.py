"""Runtime Sampler — samples actual data at pipeline stage boundaries.

Compares observed values against gamut boundaries to detect actual
clipping events in production data.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from gamut.models import (
    BoundaryReport,
    ClippingResult,
    ClippingRisk,
    FieldType,
    SampleReport,
    SampleValue,
    StageProfile,
    TypeGamut,
)
from gamut.analyzer import analyze_boundary, compute_delta_e


def sample_boundary(
    source_stage: StageProfile,
    dest_stage: StageProfile,
    source_data: list[dict[str, Any]],
    dest_data: list[dict[str, Any]] | None = None,
) -> SampleReport:
    """Sample actual data at a stage boundary.

    If dest_data is provided, compares source values to dest values directly.
    If dest_data is None, checks source values against the dest gamut profile
    to predict which values would be clipped.
    """
    samples: list[SampleValue] = []

    if dest_data is not None:
        # Compare paired rows
        for src_row, dst_row in zip(source_data, dest_data):
            for field in source_stage.fields:
                src_val = src_row.get(field.name)
                dst_val = dst_row.get(field.name)
                is_clipped = _is_value_clipped(src_val, dst_val, field.gamut)

                samples.append(SampleValue(
                    field_name=field.name,
                    value=dst_val,
                    stage=dest_stage.name,
                    timestamp=datetime.now(timezone.utc),
                    is_clipped=is_clipped,
                    original_value=src_val,
                ))
    else:
        # Predict clipping based on dest gamut
        for row in source_data:
            for field in source_stage.fields:
                val = row.get(field.name)
                dest_field = dest_stage.get_field(field.name)
                if dest_field is None:
                    samples.append(SampleValue(
                        field_name=field.name,
                        value=val,
                        stage=dest_stage.name,
                        timestamp=datetime.now(timezone.utc),
                        is_clipped=True,
                        original_value=val,
                    ))
                    continue

                is_clipped = _predict_clipping(val, dest_field.gamut)
                samples.append(SampleValue(
                    field_name=field.name,
                    value=val,
                    stage=dest_stage.name,
                    timestamp=datetime.now(timezone.utc),
                    is_clipped=is_clipped,
                    original_value=val,
                ))

    return SampleReport(
        source_stage=source_stage.name,
        dest_stage=dest_stage.name,
        samples=samples,
        timestamp=datetime.now(timezone.utc),
    )


def _is_value_clipped(
    source_val: Any,
    dest_val: Any,
    source_gamut: TypeGamut,
) -> bool:
    """Check if a value was actually clipped by comparing source and dest."""
    if source_val is None and dest_val is not None:
        return False  # NULL mapped to a value (not clipping)
    if source_val is not None and dest_val is None:
        return True  # Value became NULL (clipped)
    if source_val is None and dest_val is None:
        return False  # Both NULL

    # Compare string representations for differences
    src_str = str(source_val)
    dst_str = str(dest_val)

    if src_str != dst_str:
        # Check if it's just formatting vs actual clipping
        if source_gamut.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
            try:
                src_num = float(source_val)
                dst_num = float(dest_val)
                if abs(src_num - dst_num) > 1e-10:
                    return True
            except (ValueError, TypeError):
                return src_str != dst_str
        else:
            return True

    return False


def _predict_clipping(value: Any, dest_gamut: TypeGamut) -> bool:
    """Predict if a value would be clipped when flowing into dest_gamut."""
    if value is None:
        return not dest_gamut.nullable

    if dest_gamut.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
        try:
            num_val = float(value)
        except (ValueError, TypeError):
            return True  # Can't convert to number

        if dest_gamut.min_value is not None and num_val < dest_gamut.min_value:
            return True
        if dest_gamut.max_value is not None and num_val > dest_gamut.max_value:
            return True
        return False

    if dest_gamut.field_type == FieldType.STRING:
        str_val = str(value)
        if dest_gamut.max_length is not None and len(str_val) > dest_gamut.max_length:
            return True
        return False

    if dest_gamut.field_type in (FieldType.TIMESTAMP, FieldType.TIME):
        # Can't easily predict timezone clipping without actual datetime objects
        return False

    return False


def load_csv_data(path: str | Path) -> list[dict[str, Any]]:
    """Load sample data from a CSV file."""
    p = Path(path)
    rows: list[dict[str, Any]] = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Try to convert numeric strings
            converted: dict[str, Any] = {}
            for key, val in row.items():
                if val == "" or val is None:
                    converted[key] = None
                else:
                    converted[key] = _auto_convert(val)
            rows.append(converted)
    return rows


def load_json_data(path: str | Path) -> list[dict[str, Any]]:
    """Load sample data from a JSON file (array of objects)."""
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def _auto_convert(val: str) -> Any:
    """Try to convert a string value to its most appropriate Python type."""
    # Try integer
    try:
        return int(val)
    except ValueError:
        pass

    # Try float
    try:
        return float(val)
    except ValueError:
        pass

    # Try boolean
    if val.lower() in ("true", "yes", "1"):
        return True
    if val.lower() in ("false", "no", "0"):
        return False

    # Keep as string
    return val


def format_sample_report(report: SampleReport) -> str:
    """Format a sample report as a readable string."""
    lines: list[str] = []

    lines.append(f"Sample Report: {report.source_stage} → {report.dest_stage}")
    lines.append(f"  Total samples : {report.total_count}")
    lines.append(f"  Clipped       : {report.clipped_count}")
    lines.append(f"  Clipped %     : {report.clipped_pct:.1f}%")
    lines.append("")

    clipped_by = report.clipped_by_field()
    if clipped_by:
        lines.append("  Clipped by field:")
        for fname, count in sorted(clipped_by.items(), key=lambda x: -x[1]):
            lines.append(f"    {fname}: {count} clipped values")
        lines.append("")

    # Show first few clipped samples
    clipped_samples = [s for s in report.samples if s.is_clipped]
    if clipped_samples:
        lines.append("  Sample clipped values:")
        for s in clipped_samples[:10]:
            orig = f" (was: {s.original_value})" if s.original_value != s.value else ""
            lines.append(f"    {s.field_name}: {s.value}{orig}")
        if len(clipped_samples) > 10:
            lines.append(f"    ... and {len(clipped_samples) - 10} more")
        lines.append("")

    return "\n".join(lines)
