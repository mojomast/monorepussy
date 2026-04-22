"""Tests for utility functions."""

import pytest
from utils import format_response, validate_input, slugify, truncate


class TestFormatResponse:
    def test_success_response(self):
        result = format_response({"key": "value"})
        assert result["status"] == "success"
        assert result["data"]["key"] == "value"
        assert "timestamp" in result

    def test_error_response(self):
        result = format_response(None, status="error")
        assert result["status"] == "error"


class TestValidateInput:
    def test_required_field(self):
        errors = validate_input("", {"required": True})
        assert "required" in errors[0].lower()

    def test_min_length(self):
        errors = validate_input("ab", {"min_length": 3})
        assert len(errors) > 0

    def test_valid_input(self):
        errors = validate_input("valid", {"required": True, "min_length": 3})
        assert len(errors) == 0


class TestSlugify:
    def test_basic_slug(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars(self):
        assert slugify("Hello @ World!") == "hello-world"

    def test_multiple_spaces(self):
        assert slugify("Hello    World") == "hello-world"


class TestTruncate:
    def test_short_string(self):
        assert truncate("short", length=10) == "short"

    def test_long_string(self):
        result = truncate("this is a very long string", length=10)
        assert len(result) == 10
        assert result.endswith("...")
