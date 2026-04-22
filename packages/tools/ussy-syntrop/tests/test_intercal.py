"""Tests for the INTERCAL backend."""

import pytest

from ussy_syntrop.backends.intercal import IntercalBackend, IntercalInstruction
from ussy_syntrop.ir import IRFunction, IRModule, IRNode, IRNodeType


class TestIntercalInstruction:
    """Tests for IntercalInstruction dataclass."""

    def test_create_instruction(self):
        instr = IntercalInstruction(opcode="DO", operands=["READ OUT x"])
        assert instr.opcode == "DO"
        assert instr.operands == ["READ OUT x"]
        assert instr.label == ""
        assert instr.probability == 1.0

    def test_instruction_with_label(self):
        instr = IntercalInstruction(opcode="DO", operands=["x <- 1"], label="L001")
        assert instr.label == "L001"

    def test_instruction_with_come_from(self):
        instr = IntercalInstruction(
            opcode="COME_FROM",
            operands=["L002"],
            probability=0.5,
            come_from="L002",
        )
        assert instr.come_from == "L002"
        assert instr.probability == 0.5


class TestIntercalBackend:
    """Tests for the IntercalBackend."""

    def test_backend_name(self):
        backend = IntercalBackend()
        assert backend.name == "intercal"

    def test_backend_in_registry(self):
        from ussy_syntrop.backends import BACKEND_REGISTRY
        assert "intercal" in BACKEND_REGISTRY

    def test_compile_simple_function(self):
        func = IRFunction(name="test", body=IRNode(IRNodeType.BLOCK))
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert len(instructions) > 0
        assert any("GIVE UP" in " ".join(i.operands) for i in instructions)

    def test_compile_function_with_for_each(self):
        func = IRFunction(
            name="process",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(
                        IRNodeType.FOR_EACH,
                        attributes={"var": "item", "iterable": "items"},
                        children=[
                            IRNode(IRNodeType.ASSIGN, attributes={"name": "x", "value": "item"}),
                        ],
                    )
                ],
            ),
        )
        backend = IntercalBackend(come_from_probability=0.5)
        instructions = backend.compile_function(func)
        assert any(i.opcode == "COME_FROM" for i in instructions)

    def test_compile_function_with_if(self):
        func = IRFunction(
            name="check",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(
                        IRNodeType.IF,
                        attributes={"condition": "x > 0"},
                        children=[
                            IRNode(IRNodeType.RETURN, attributes={"value": "x"}),
                        ],
                    )
                ],
            ),
        )
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert any("ABSTAIN" in " ".join(i.operands) for i in instructions)

    def test_compile_module(self):
        mod = IRModule(
            name="test_mod",
            functions=[IRFunction(name="foo", body=IRNode(IRNodeType.BLOCK))],
        )
        backend = IntercalBackend()
        instructions = backend.compile_module(mod)
        assert len(instructions) > 0
        assert any("Module: test_mod" in i.comment for i in instructions)

    def test_format_intercal(self):
        instructions = [
            IntercalInstruction(opcode="DO", operands=["READ OUT test"], label="L001"),
            IntercalInstruction(opcode="DO", operands=["x <- 1"]),
            IntercalInstruction(opcode="COME_FROM", operands=["L002"], probability=0.5),
            IntercalInstruction(opcode="DO", operands=["GIVE UP"]),
        ]
        backend = IntercalBackend()
        output = backend.format_intercal(instructions)
        assert "L001" in output
        assert "GIVE UP" in output
        assert "%50" in output

    def test_simulate_execution(self):
        instructions = [
            IntercalInstruction(opcode="DO", operands=["x <- 1"]),
            IntercalInstruction(opcode="DO", operands=["GIVE UP"]),
        ]
        backend = IntercalBackend(seed=42)
        result = backend.simulate_execution(instructions)
        assert "output" in result
        assert "divergences" in result
        assert "steps" in result

    def test_simulate_with_come_from(self):
        instructions = [
            IntercalInstruction(opcode="DO", operands=["x <- 1"], label="L001"),
            IntercalInstruction(
                opcode="COME_FROM",
                operands=["L001"],
                probability=1.0,  # Always redirect
            ),
            IntercalInstruction(opcode="DO", operands=["GIVE UP"]),
        ]
        backend = IntercalBackend(seed=42)
        result = backend.simulate_execution(instructions)
        assert len(result["divergences"]) > 0
        assert result["came_from_triggered"] > 0

    def test_simulate_max_steps(self):
        """Infinite COME FROM loop should hit max steps."""
        instructions = [
            IntercalInstruction(opcode="DO", operands=["x <- 1"], label="L001"),
            IntercalInstruction(
                opcode="COME_FROM",
                operands=["L001"],
                probability=1.0,
            ),
        ]
        backend = IntercalBackend(seed=42)
        result = backend.simulate_execution(instructions)
        assert result["steps"] == 10000

    def test_run_module(self):
        mod = IRModule(
            name="test",
            functions=[IRFunction(name="foo", body=IRNode(IRNodeType.BLOCK))],
        )
        backend = IntercalBackend(come_from_probability=1.0, seed=42)
        result = backend.run(mod)
        assert result.probe_name == "intercal-backend"

    def test_come_from_probability(self):
        backend = IntercalBackend(come_from_probability=0.5)
        assert backend.come_from_probability == 0.5

    def test_seed_reproducibility(self):
        """Same seed should produce same simulation results."""
        instructions = [
            IntercalInstruction(opcode="DO", operands=["x <- 1"], label="L001"),
            IntercalInstruction(
                opcode="COME_FROM",
                operands=["L001"],
                probability=0.5,
            ),
            IntercalInstruction(opcode="DO", operands=["GIVE UP"]),
        ]
        backend1 = IntercalBackend(seed=42)
        backend2 = IntercalBackend(seed=42)
        result1 = backend1.simulate_execution(instructions)
        result2 = backend2.simulate_execution(instructions)
        assert result1["came_from_triggered"] == result2["came_from_triggered"]

    def test_compile_assign_node(self):
        func = IRFunction(
            name="assign_test",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(IRNodeType.ASSIGN, attributes={"name": "x", "value": "42"}),
                ],
            ),
        )
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert any("x <- 42" in " ".join(i.operands) for i in instructions)

    def test_compile_return_node(self):
        func = IRFunction(
            name="ret_test",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(IRNodeType.RETURN, attributes={"value": "x"}),
                ],
            ),
        )
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert any("READ OUT x" in " ".join(i.operands) for i in instructions)

    def test_compile_mutate_node(self):
        func = IRFunction(
            name="mut_test",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(IRNodeType.MUTATE, attributes={"target": "result", "operation": "APPEND"}),
                ],
            ),
        )
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert any("result APPEND" in " ".join(i.operands) for i in instructions)

    def test_compile_accum_node(self):
        func = IRFunction(
            name="accum_test",
            body=IRNode(
                IRNodeType.BLOCK,
                children=[
                    IRNode(
                        IRNodeType.ACCUM,
                        attributes={"name": "acc"},
                        children=[
                            IRNode(IRNodeType.ASSIGN, attributes={"name": "acc", "value": "0"}),
                        ],
                    ),
                ],
            ),
        )
        backend = IntercalBackend()
        instructions = backend.compile_function(func)
        assert any("STASH acc" in " ".join(i.operands) for i in instructions)
