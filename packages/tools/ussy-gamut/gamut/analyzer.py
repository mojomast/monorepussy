"""Clipping Analyzer — computes gamut intersections and clipping metrics.

At each stage boundary, computes:
- Clipping risk (is source gamut wider than destination?)
- Clipping severity (Delta E analogue — how much info is lost?)
- Rendering intent classification
"""

from __future__ import annotations

import math
from typing import Any

from gamut.models import (
    BoundaryReport,
    ClippingResult,
    ClippingRisk,
    FieldType,
    FieldProfile,
    PipelineDAG,
    RenderingIntent,
    StageProfile,
    TypeGamut,
)


# ---------------------------------------------------------------------------
# Delta-E computation
# ---------------------------------------------------------------------------

# Weights for different dimensions of gamut comparison
_WEIGHT_NUMERIC_RANGE = 0.30
_WEIGHT_PRECISION = 0.25
_WEIGHT_TIMEZONE = 0.25
_WEIGHT_CHARSET = 0.10
_WEIGHT_NULLABLE = 0.10


def compute_delta_e(source: TypeGamut, dest: TypeGamut) -> float:
    """Compute a Delta-E analogue measuring information loss.

    Returns a float in [0, 100] where:
      0  = no information loss (perfect fidelity)
      100 = total information loss

    Inspired by CIE Delta E: measures perceptual difference between
    the source and destination gamuts across multiple dimensions.
    """
    de = 0.0

    # 1. Numeric range compression
    range_loss = _numeric_range_loss(source, dest)
    de += _WEIGHT_NUMERIC_RANGE * range_loss * 100

    # 2. Precision / scale loss
    prec_loss = _precision_loss(source, dest)
    de += _WEIGHT_PRECISION * prec_loss * 100

    # 3. Timezone information loss
    tz_loss = _timezone_loss(source, dest)
    de += _WEIGHT_TIMEZONE * tz_loss * 100

    # 4. Charset loss
    charset_loss = _charset_loss(source, dest)
    de += _WEIGHT_CHARSET * charset_loss * 100

    # 5. Nullable constraint violation
    null_loss = _nullable_loss(source, dest)
    de += _WEIGHT_NULLABLE * null_loss * 100

    return min(de, 100.0)


def _numeric_range_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """Fraction of source range not representable in destination."""
    import math

    if source.field_type not in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
        return 0.0
    if dest.field_type not in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
        return 1.0  # Type category change = total loss

    src_min = source.min_value
    src_max = source.max_value
    dst_min = dest.min_value
    dst_max = dest.max_value

    # If any are None (unbounded), handle specially
    if src_min is None or src_max is None:
        if dst_min is None and dst_max is None:
            return 0.0  # Both unbounded
        return 0.5  # Source unbounded, dest bounded -> some loss

    if dst_min is None and dst_max is None:
        return 0.0  # Dest unbounded, source bounded -> no loss

    # Handle infinite values from float overflow
    src_inf = math.isinf(src_min) or math.isinf(src_max)
    dst_inf = math.isinf(dst_min) or math.isinf(dst_max)

    if src_inf:
        if dst_inf:
            return 0.0  # Both effectively unbounded
        return 0.8  # Source has huge range, dest is bounded -> significant loss

    src_range = src_max - src_min
    if src_range <= 0 or math.isnan(src_range):
        return 0.0

    # Compute how much of source range is outside dest range
    clipped_min = max(0, dst_min - src_min) if dst_min is not None and not math.isinf(dst_min) else 0
    clipped_max = max(0, src_max - dst_max) if dst_max is not None and not math.isinf(dst_max) else 0
    clipped = clipped_min + clipped_max

    ratio = clipped / src_range
    if math.isnan(ratio) or math.isinf(ratio):
        return 0.5

    return min(ratio, 1.0)


def _precision_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """Fraction of precision lost in the conversion."""
    if source.precision is None:
        return 0.0  # Variable precision, assume OK
    if dest.precision is None:
        return 0.0  # Variable precision dest, assume OK

    if dest.precision >= source.precision:
        if source.scale is not None and dest.scale is not None:
            if dest.scale >= source.scale:
                return 0.0
            # Scale loss
            return (source.scale - dest.scale) / max(source.scale, 1)
        return 0.0

    # Precision loss
    loss = (source.precision - dest.precision) / max(source.precision, 1)
    if source.scale is not None and dest.scale is not None:
        if dest.scale < source.scale:
            # Both precision and scale loss
            scale_loss = (source.scale - dest.scale) / max(source.scale, 1)
            loss = max(loss, scale_loss)
    return min(loss, 1.0)


def _timezone_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """Timezone information loss."""
    if source.field_type not in (FieldType.TIMESTAMP, FieldType.TIME):
        return 0.0
    if dest.field_type not in (FieldType.TIMESTAMP, FieldType.TIME):
        return 1.0  # Type category change

    if source.timezone_aware and not dest.timezone_aware:
        return 1.0  # Full timezone loss
    if not source.timezone_aware and dest.timezone_aware:
        return 0.0  # Gaining timezone is fine

    # Both same timezone awareness, check precision
    if source.tz_precision is not None and dest.tz_precision is not None:
        if dest.tz_precision < source.tz_precision:
            return (source.tz_precision - dest.tz_precision) / max(source.tz_precision, 1)

    return 0.0


def _charset_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """Character set information loss for strings."""
    if source.field_type != FieldType.STRING:
        return 0.0
    if dest.field_type != FieldType.STRING:
        return 1.0  # Not a string at all

    if source.charset and dest.charset:
        src_charset = source.charset.upper()
        dst_charset = dest.charset.upper()

        if src_charset == dst_charset:
            # Same charset, check length
            return _length_loss(source, dest)

        # Known charset subsets
        if src_charset == "UTF-8" and dst_charset in ("LATIN1", "ISO-8859-1", "ASCII"):
            return 0.5  # UTF-8 to narrower charset = significant loss
        if src_charset == "UTF-8" and dst_charset == "US-ASCII":
            return 0.7

    return _length_loss(source, dest)


def _length_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """String length truncation loss."""
    if source.max_length is None:
        if dest.max_length is not None:
            return 0.3  # Unbounded source, bounded dest
        return 0.0

    if dest.max_length is None:
        return 0.0  # Bounded source, unbounded dest

    if dest.max_length >= source.max_length:
        return 0.0

    return (source.max_length - dest.max_length) / max(source.max_length, 1)


def _nullable_loss(source: TypeGamut, dest: TypeGamut) -> float:
    """Loss from nullable to non-nullable constraint."""
    if source.nullable and not dest.nullable:
        return 1.0  # Potential NOT NULL violation
    return 0.0


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

def classify_risk(delta_e: float) -> ClippingRisk:
    """Classify clipping risk based on Delta E value.

    Thresholds (mirrors color science perceptibility scales):
      0.0   – NONE    (imperceptible)
      < 1.0 – LOW     (just noticeable)
      < 5.0 – MEDIUM  (clearly noticeable)
      < 20  – HIGH    (significant)
      >= 20 – CRITICAL (severe)
    """
    if delta_e == 0.0:
        return ClippingRisk.NONE
    if delta_e < 1.0:
        return ClippingRisk.LOW
    if delta_e < 5.0:
        return ClippingRisk.MEDIUM
    if delta_e < 20.0:
        return ClippingRisk.HIGH
    return ClippingRisk.CRITICAL


# ---------------------------------------------------------------------------
# Rendering intent classification
# ---------------------------------------------------------------------------

def classify_rendering_intent(source: TypeGamut, dest: TypeGamut) -> RenderingIntent:
    """Classify the rendering intent of a gamut conversion.

    * Perceptual: best-effort mapping that preserves relationships
      (e.g. rounding, truncating precision)
    * Absolute Colorimetric: error/reject on out-of-gamut
      (e.g. NOT NULL constraint, unique constraint)
    * Saturation: clamping to nearest in-gamut value
      (e.g. integer overflow, string truncation)
    """
    # NOT NULL violation = absolute colorimetric
    if source.nullable and not dest.nullable:
        return RenderingIntent.ABSOLUTE_COLORIMETRIC

    # String length truncation = saturation (clamping)
    if source.field_type == FieldType.STRING and dest.field_type == FieldType.STRING:
        if source.max_length is not None and dest.max_length is not None:
            if dest.max_length < source.max_length:
                return RenderingIntent.SATURATION

    # Timezone drop = saturation (clamped to local)
    if source.timezone_aware and dest.timezone_aware is False:
        if dest.field_type in (FieldType.TIMESTAMP, FieldType.TIME):
            return RenderingIntent.SATURATION

    # Numeric precision/range loss = perceptual (rounding)
    if source.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
        if dest.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
            return RenderingIntent.PERCEPTUAL

    # Default to perceptual
    return RenderingIntent.PERCEPTUAL


# ---------------------------------------------------------------------------
# Clipped value examples
# ---------------------------------------------------------------------------

def generate_clipped_examples(source: TypeGamut, dest: TypeGamut) -> list[str]:
    """Generate concrete example values that would be clipped."""
    examples: list[str] = []

    # Numeric range clipping
    if source.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
        if dest.field_type in (FieldType.INTEGER, FieldType.FLOAT, FieldType.DECIMAL):
            if dest.max_value is not None and source.max_value is not None:
                if dest.max_value < source.max_value:
                    examples.append(f"value={source.max_value:.0f} exceeds dest max={dest.max_value:.0f}")
            if dest.min_value is not None and source.min_value is not None:
                if dest.min_value > source.min_value:
                    examples.append(f"value={source.min_value:.0f} below dest min={dest.min_value:.0f}")

    # Precision loss
    if source.precision is not None and dest.precision is not None:
        if dest.precision < source.precision:
            diff = source.precision - dest.precision
            examples.append(f"precision loss: {source.precision} → {dest.precision} digits ({diff} lost)")

    # Scale loss
    if source.scale is not None and dest.scale is not None:
        if dest.scale < source.scale:
            diff = source.scale - dest.scale
            examples.append(f"scale loss: {source.scale} → {dest.scale} decimal places ({diff} lost)")

    # Timezone loss
    if source.timezone_aware and dest.timezone_aware is False:
        if source.field_type in (FieldType.TIMESTAMP, FieldType.TIME):
            examples.append("timezone information dropped (TIMESTAMPTZ → TIMESTAMP)")

    # Timezone precision loss
    if source.tz_precision is not None and dest.tz_precision is not None:
        if dest.tz_precision < source.tz_precision:
            diff = source.tz_precision - dest.tz_precision
            examples.append(f"temporal precision loss: {source.tz_precision} → {dest.tz_precision} digits ({diff} lost)")

    # Charset loss
    if source.charset and dest.charset:
        if source.charset.upper() == "UTF-8" and dest.charset.upper() in ("LATIN1", "ISO-8859-1", "ASCII", "US-ASCII"):
            examples.append(f"charset narrowing: {source.charset} → {dest.charset}")

    # Length truncation
    if source.max_length is not None and dest.max_length is not None:
        if dest.max_length < source.max_length:
            examples.append(f"string truncation: max {source.max_length} → {dest.max_length} chars")

    # Nullable to non-nullable
    if source.nullable and not dest.nullable:
        examples.append("NULL values will be rejected (nullable → NOT NULL)")

    return examples


# ---------------------------------------------------------------------------
# Main analysis functions
# ---------------------------------------------------------------------------

def analyze_field(source: FieldProfile, dest: FieldProfile) -> ClippingResult:
    """Analyze clipping for a single field at a stage boundary."""
    src_g = source.gamut
    dst_g = dest.gamut

    delta_e = compute_delta_e(src_g, dst_g)
    risk = classify_risk(delta_e)
    intent = classify_rendering_intent(src_g, dst_g)
    examples = generate_clipped_examples(src_g, dst_g)

    notes: list[str] = []
    if src_g.field_type != dst_g.field_type:
        notes.append(f"type category change: {src_g.field_type.value} → {dst_g.field_type.value}")
    if src_g.system != dst_g.system:
        notes.append(f"system change: {src_g.system} → {dst_g.system}")

    return ClippingResult(
        field_name=source.name,
        source_gamut=src_g,
        dest_gamut=dst_g,
        risk=risk,
        delta_e=round(delta_e, 4),
        rendering_intent=intent,
        clipped_examples=examples,
        notes=notes,
    )


def analyze_boundary(source: StageProfile, dest: StageProfile) -> BoundaryReport:
    """Analyze clipping at a stage boundary between two StageProfiles."""
    results: list[ClippingResult] = []

    # Match fields by name
    dest_fields = {f.name: f for f in dest.fields}

    for src_field in source.fields:
        dst_field = dest_fields.get(src_field.name)
        if dst_field is None:
            # Field exists in source but not dest = total loss
            cr = ClippingResult(
                field_name=src_field.name,
                source_gamut=src_field.gamut,
                dest_gamut=TypeGamut(
                    system=dest.system,
                    type_name="<missing>",
                    field_type=FieldType.UNKNOWN,
                    nullable=False,
                ),
                risk=ClippingRisk.CRITICAL,
                delta_e=100.0,
                rendering_intent=RenderingIntent.ABSOLUTE_COLORIMETRIC,
                clipped_examples=["field missing in destination"],
                notes=["field dropped"],
            )
            results.append(cr)
        else:
            results.append(analyze_field(src_field, dst_field))

    # Check for fields only in dest (added fields, not a clipping concern)
    src_names = {f.name for f in source.fields}
    for dst_field in dest.fields:
        if dst_field.name not in src_names:
            cr = ClippingResult(
                field_name=dst_field.name,
                source_gamut=TypeGamut(
                    system=source.system,
                    type_name="<missing>",
                    field_type=FieldType.UNKNOWN,
                    nullable=True,
                ),
                dest_gamut=dst_field.gamut,
                risk=ClippingRisk.NONE,
                delta_e=0.0,
                notes=["field added in destination"],
            )
            results.append(cr)

    return BoundaryReport(
        source_stage=source.name,
        dest_stage=dest.name,
        results=results,
    )


def analyze_pipeline(dag: PipelineDAG) -> list[BoundaryReport]:
    """Analyze all boundaries in a pipeline DAG."""
    reports: list[BoundaryReport] = []
    for src, dst in dag.boundary_pairs():
        reports.append(analyze_boundary(src, dst))
    return reports
