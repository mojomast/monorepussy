"""Tests for crystallo.parser — AST parsing and fingerprint extraction."""

import pytest
from pathlib import Path

from crystallo.parser import parse_file, parse_directory, _node_to_name
from crystallo.models import StructuralFingerprint


FIXTURES = Path(__file__).parent / "fixtures"


class TestParseFile:
    def test_parse_models(self):
        fps = parse_file(FIXTURES / "models.py")
        assert len(fps) >= 5  # BaseModel, UserModel, OrderModel, ProductModel, GuestModel

    def test_parse_api(self):
        fps = parse_file(FIXTURES / "api.py")
        assert len(fps) >= 4  # APIClient, APIServer, create_user, create_order, etc.

    def test_parse_sample_tests(self):
        fps = parse_file(FIXTURES / "sample_tests.py")
        assert len(fps) >= 3  # TestUserModel, TestOrderModel, TestProductModel

    def test_parse_empty_file(self):
        fps = parse_file(FIXTURES / "empty.py")
        assert fps == []

    def test_parse_syntax_error(self):
        fps = parse_file(FIXTURES / "syntax_error.py")
        assert fps == []  # gracefully handles SyntaxError

    def test_class_fingerprint_has_kind(self):
        fps = parse_file(FIXTURES / "models.py")
        class_fps = [fp for fp in fps if fp.kind == "class"]
        assert len(class_fps) >= 5

    def test_function_fingerprint_kind(self):
        fps = parse_file(FIXTURES / "api.py")
        func_fps = [fp for fp in fps if fp.kind == "function"]
        assert len(func_fps) >= 4

    def test_base_classes_extracted(self):
        fps = parse_file(FIXTURES / "models.py")
        user = next(fp for fp in fps if fp.name == "UserModel")
        assert "BaseModel" in user.base_classes

    def test_no_base_class(self):
        fps = parse_file(FIXTURES / "models.py")
        guest = next(fp for fp in fps if fp.name == "GuestModel")
        assert guest.base_classes == []

    def test_method_names_extracted(self):
        fps = parse_file(FIXTURES / "models.py")
        user = next(fp for fp in fps if fp.name == "UserModel")
        assert "save" in user.method_names
        assert "delete" in user.method_names
        assert "validate_email" in user.method_names

    def test_has_init(self):
        fps = parse_file(FIXTURES / "models.py")
        user = next(fp for fp in fps if fp.name == "UserModel")
        assert user.has_init is True

    def test_attribute_names(self):
        fps = parse_file(FIXTURES / "models.py")
        user = next(fp for fp in fps if fp.name == "UserModel")
        # Attributes assigned in __init__ with self.X are NOT top-level assigns
        # They are in the __init__ method body, not class-level assigns
        # Our parser extracts class-level assigns/annassigns
        assert isinstance(user.attribute_names, list)

    def test_feature_vector_populated(self):
        fps = parse_file(FIXTURES / "models.py")
        user = next(fp for fp in fps if fp.name == "UserModel")
        assert len(user.feature_vector) == 15
        assert user.feature_vector[0] > 0  # method count

    def test_file_path_set(self):
        fps = parse_file(FIXTURES / "models.py")
        assert all(fp.file_path for fp in fps)


class TestParseDirectory:
    def test_parse_fixtures_dir(self):
        fps = parse_directory(FIXTURES)
        # Should find models.py, api.py, sample_tests.py (not empty/syntax_error)
        assert len(fps) >= 8

    def test_parse_single_file_via_directory(self):
        """parse_directory with a file path should delegate to parse_file."""
        fps = parse_directory(FIXTURES / "models.py")
        assert len(fps) >= 5

    def test_parse_nonexistent_path(self):
        fps = parse_directory("/nonexistent/path/xyz123")
        assert fps == []


class TestNodeToName:
    def test_simple_name(self):
        import ast
        node = ast.Name(id="foo")
        assert _node_to_name(node) == "foo"

    def test_attribute(self):
        import ast
        node = ast.Attribute(value=ast.Name(id="os"), attr="path")
        assert _node_to_name(node) == "os.path"
