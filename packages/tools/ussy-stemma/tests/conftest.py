"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from stemma.models import Witness

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def witness_a() -> Witness:
    return Witness(
        label="A",
        source="payment_a.py",
        lines=[
            "def process_payment(order):",
            "    validate_order(order)",
            "    charge = calc(order)",
            "    if charge > 0:",
            "        apply_fees(charge)",
            "        charge = adjust_for_region(charge)",
            "    receipt = generate(charge)",
            "    log.info(f\"Processed: {receipt.id}\")",
            "    return Receipt(receipt)",
        ],
    )


@pytest.fixture
def witness_b() -> Witness:
    return Witness(
        label="B",
        source="payment_b.py",
        lines=[
            "def process_payment(order):",
            "    validate_order(order)",
            "    charge = calc(order)",
            "    if charge > 0:",
            "        apply_fees(charge)",
            "        charge = adjust_for_region(charge)",
            "    receipt = generate(charge)",
            "    log.info(f\"Processed: {receipt.id}\")",
            "    return Receipt(receipt)",
        ],
    )


@pytest.fixture
def witness_c() -> Witness:
    return Witness(
        label="C",
        source="payment_c.py",
        lines=[
            "def process_payment(order):",
            "    validate_order(order)",
            "    charge = compute(order)",
            "    if charge > 0:",
            "        apply_fees(charge)",
            "        charge = adjust_for_region(charge)",
            "    receipt = generate(charge)",
            "    return Receipt(receipt)",
        ],
    )


@pytest.fixture
def witness_d() -> Witness:
    return Witness(
        label="D",
        source="payment_d.py",
        lines=[
            "def process_payment(order):",
            "    validate_order(order)",
            "    charge = compute(order)",
            "    if charge >= 0:",
            "        apply_fees(charge)",
            "        charge = adjust_for_region(charge)",
            "    receipt = generate(charge)",
            "    log.info(f\"Processed: {receipt.id}\")",
            "    return Receipt(receipt)",
        ],
    )


@pytest.fixture
def witness_e() -> Witness:
    return Witness(
        label="E",
        source="payment_e.py",
        lines=[
            "def process_payment(order):",
            "    validate_order(order)",
            "    charge = compute(order)",
            "    if charge >= 0:",
            "        apply_fees(charge)",
            "        charge = adjust_for_region(charge)",
            "    receipt = generate(charge)",
            "    return r",
        ],
    )


@pytest.fixture
def all_witnesses(witness_a, witness_b, witness_c, witness_d, witness_e):
    return [witness_a, witness_b, witness_c, witness_d, witness_e]
