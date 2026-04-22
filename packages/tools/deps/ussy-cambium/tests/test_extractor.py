"""Tests for Cambium extractor module."""

from __future__ import annotations

import os
import tempfile

import pytest

from cambium.extractor import (
    extract_interface,
    extract_interfaces_from_directory,
    extract_interface_from_file,
)
from cambium.models import InterfaceInfo


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestExtractInterface:
    """Tests for extract_interface function."""

    def test_empty_source(self):
        info = extract_interface("", "empty")
        assert info.name == "empty"
        assert len(info.exported_types) == 0
        assert len(info.exported_functions) == 0

    def test_class_extraction(self):
        source = """
class MyClass:
    def method_a(self, x: int) -> str:
        pass
    def method_b(self):
        pass
"""
        info = extract_interface(source, "test_mod")
        assert "MyClass" in info.exported_types
        assert "MyClass.method_a" in info.method_signatures
        assert "MyClass.method_b" in info.method_signatures

    def test_function_extraction(self):
        source = """
def hello(name: str) -> str:
    return f"Hello {name}"

def add(a: int, b: int) -> int:
    return a + b
"""
        info = extract_interface(source, "funcs")
        assert "hello" in info.exported_functions
        assert "add" in info.exported_functions

    def test_async_function_extraction(self):
        source = """
async def fetch_data(url: str) -> dict:
    pass
"""
        info = extract_interface(source, "async_mod")
        assert "fetch_data" in info.exported_functions

    def test_all_filtering(self):
        source = """
__all__ = ["PublicClass", "public_func"]

class PublicClass:
    pass

class PrivateClass:
    pass

def public_func():
    pass

def private_func():
    pass
"""
        info = extract_interface(source, "filtered")
        assert "PublicClass" in info.exported_types
        assert "PrivateClass" not in info.exported_types
        assert "public_func" in info.exported_functions
        assert "private_func" not in info.exported_functions

    def test_signature_extraction(self):
        source = """
def complex(a: int, b: str = "hello", *args, **kwargs):
    pass
"""
        info = extract_interface(source, "sigs")
        sig = info.method_signatures.get("complex", [])
        assert len(sig) > 0
        # Should contain the parameter names
        param_names = [p.split(":")[0].strip("*") for p in sig]
        assert "a" in param_names

    def test_precondition_extraction(self):
        source = """
def process(data):
    assert data
    assert len(data) > 0
    return data
"""
        info = extract_interface(source, "precon")
        assert "data" in info.preconditions

    def test_syntax_error_returns_empty(self):
        source = "def broken(:\n"
        info = extract_interface(source, "broken")
        assert info.name == "broken"
        assert len(info.exported_types) == 0

    def test_class_with_annotations(self):
        source = """
class Typed:
    name: str
    age: int
"""
        info = extract_interface(source, "typed")
        assert "Typed" in info.exported_types


class TestExtractFromFile:
    """Tests for extract_interface_from_file."""

    def test_consumer_fixture(self):
        path = os.path.join(FIXTURES_DIR, "consumer.py")
        info = extract_interface_from_file(path)
        assert info.name == "consumer"
        assert "AuthClient" in info.exported_types
        assert "UserManager" in info.exported_types

    def test_provider_fixture(self):
        path = os.path.join(FIXTURES_DIR, "provider.py")
        info = extract_interface_from_file(path)
        assert info.name == "provider"
        assert "AuthClient" in info.exported_types
        assert "RoleManager" in info.exported_types

    def test_nonexistent_file(self):
        info = extract_interface_from_file("/nonexistent/file.py")
        assert info.name  # should have a name from the path

    def test_empty_module(self):
        path = os.path.join(FIXTURES_DIR, "empty_module.py")
        info = extract_interface_from_file(path)
        assert len(info.exported_types) == 0


class TestExtractFromDirectory:
    """Tests for extract_interfaces_from_directory."""

    def test_fixtures_directory(self):
        result = extract_interfaces_from_directory(FIXTURES_DIR)
        assert len(result) > 0
        assert "consumer" in result or "provider" in result

    def test_nonexistent_directory(self):
        result = extract_interfaces_from_directory("/nonexistent/dir")
        assert len(result) == 0
