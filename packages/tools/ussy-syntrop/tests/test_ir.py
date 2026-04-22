"""Tests for the Syntrop IR module."""

import pytest

from ussy_syntrop.ir import (
    IRFunction,
    IRModule,
    IRNode,
    IRNodeType,
    Mutability,
    ProbeResult,
    ScanResult,
    DiffResult,
)


class TestIRNodeType:
    """Tests for IRNodeType enum."""

    def test_all_node_types_exist(self):
        """All expected node types should be defined."""
        expected = [
            "FUNCTION", "BLOCK", "ASSIGN", "RETURN", "FOR_EACH", "FOR_RANGE",
            "WHILE", "IF", "CALL", "MUTATE", "ACCUM", "BINARY_OP", "UNARY_OP",
            "LITERAL", "IDENTIFIER", "SUBSCRIPT", "ATTRIBUTE", "COMPARE", "BOOLEAN_OP",
        ]
        for name in expected:
            assert hasattr(IRNodeType, name)

    def test_node_types_are_unique(self):
        """All node type values should be unique."""
        values = [t.value for t in IRNodeType]
        assert len(values) == len(set(values))


class TestMutability:
    """Tests for Mutability enum."""

    def test_mutability_values(self):
        assert Mutability.IMMUTABLE.value == "immutable"
        assert Mutability.ACCUMULATOR.value == "accumulator"
        assert Mutability.MUTABLE.value == "mutable"


class TestIRNode:
    """Tests for IRNode dataclass."""

    def test_create_simple_node(self):
        node = IRNode(IRNodeType.LITERAL, attributes={"value": 42})
        assert node.node_type == IRNodeType.LITERAL
        assert node.attributes["value"] == 42
        assert node.children == []

    def test_create_node_with_children(self):
        child1 = IRNode(IRNodeType.LITERAL, attributes={"value": 1})
        child2 = IRNode(IRNodeType.LITERAL, attributes={"value": 2})
        parent = IRNode(IRNodeType.BINARY_OP, children=[child1, child2])
        assert len(parent.children) == 2
        assert parent.children[0].attributes["value"] == 1

    def test_pretty_print(self):
        node = IRNode(
            IRNodeType.IF,
            attributes={"condition": "x > 0"},
            children=[
                IRNode(IRNodeType.RETURN, attributes={"value": "x"}),
            ],
        )
        output = node.pretty()
        assert "IF" in output
        assert "condition='x > 0'" in output
        assert "RETURN" in output

    def test_pretty_print_empty_node(self):
        node = IRNode(IRNodeType.BLOCK)
        output = node.pretty()
        assert "BLOCK" in output

    def test_default_attributes(self):
        node = IRNode(IRNodeType.BLOCK)
        assert node.children == []
        assert node.attributes == {}


class TestIRFunction:
    """Tests for IRFunction dataclass."""

    def test_create_function(self):
        func = IRFunction(name="test", params=[("x", "int")])
        assert func.name == "test"
        assert func.params == [("x", "int")]
        assert func.return_type is None

    def test_function_with_return_type(self):
        func = IRFunction(name="add", return_type="int")
        assert func.return_type == "int"

    def test_pretty_print(self):
        func = IRFunction(
            name="process",
            params=[("items", "List")],
            return_type="List",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[IRNode(IRNodeType.RETURN, attributes={"value": "items"})],
            ),
        )
        output = func.pretty()
        assert "FUNC process(items: List) -> List" in output
        assert "RETURN" in output


class TestIRModule:
    """Tests for IRModule dataclass."""

    def test_create_module(self):
        mod = IRModule(name="test_module")
        assert mod.name == "test_module"
        assert mod.functions == []
        assert mod.globals_ == []

    def test_module_with_functions(self):
        func = IRFunction(name="foo")
        mod = IRModule(name="mod", functions=[func])
        assert len(mod.functions) == 1

    def test_pretty_print(self):
        func = IRFunction(name="bar")
        mod = IRModule(name="mymod", functions=[func], globals_=[("x", Mutability.MUTABLE, 0)])
        output = mod.pretty()
        assert "MODULE mymod:" in output
        assert "GLOBAL x" in output
        assert "FUNC bar" in output


class TestProbeResult:
    """Tests for ProbeResult dataclass."""

    def test_create_result_no_divergence(self):
        result = ProbeResult(
            probe_name="test",
            original_output=[1, 2, 3],
            probed_output=[1, 2, 3],
            diverged=False,
            explanation="No divergence",
        )
        assert not result.diverged
        assert result.severity == "info"

    def test_create_result_with_divergence(self):
        result = ProbeResult(
            probe_name="test",
            original_output=[1, 2, 3],
            probed_output=[3, 2, 1],
            diverged=True,
            divergence_type="order-flip",
            explanation="Order changed",
            severity="warning",
        )
        assert result.diverged
        assert result.divergence_type == "order-flip"

    def test_default_fields(self):
        result = ProbeResult(probe_name="test")
        assert result.original_output is None
        assert result.probed_output is None
        assert result.diverged is False
        assert result.divergence_type == ""
        assert result.severity == "info"
        assert result.metadata == {}


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_create_scan_result(self):
        result = ScanResult(path="/tmp/test.py")
        assert result.path == "/tmp/test.py"
        assert result.assumptions == []
        assert result.probe_results == []

    def test_scan_result_with_data(self):
        result = ScanResult(
            path="/tmp/test.py",
            assumptions=[{"kind": "iteration-order", "line": 5}],
            summary="1 warning",
        )
        assert len(result.assumptions) == 1
        assert result.summary == "1 warning"


class TestDiffResult:
    """Tests for DiffResult dataclass."""

    def test_create_diff_result(self):
        result = DiffResult(
            file_path="test.py",
            modes_compared=["randomize-iteration"],
            consistent=True,
        )
        assert result.consistent
        assert len(result.modes_compared) == 1

    def test_diff_result_with_divergences(self):
        result = DiffResult(
            file_path="test.py",
            modes_compared=["randomize-iteration", "alias-state"],
            divergences=[{"probe": "randomize-iteration", "type": "order-flip"}],
            consistent=False,
        )
        assert not result.consistent
        assert len(result.divergences) == 1
