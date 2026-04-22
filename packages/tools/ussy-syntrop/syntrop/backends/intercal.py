"""INTERCAL backend: proof-of-concept esolang compiler.

INTERCAL (Compiler Language With No Pronounceable Acronym) is famous for:
- COME FROM statements (reverse of GOTO)
- Random control flow via % probabilities
- ABSTAIN/REINSTATE to disable/enable statements

This backend is a proof-of-concept that demonstrates how esolang
compilation can reveal hidden control-flow assumptions. We implement
a simplified INTERCAL-like execution model that:
1. Parses the IR
2. Generates pseudo-INTERCAL code
3. Simulates execution with randomized COME FROM behavior

Note: This is NOT a full INTERCAL compiler. It's a demonstration that
compilation to a different computational model can reveal semantic bugs.
"""

from __future__ import annotations

import random
import textwrap
from dataclasses import dataclass, field
from typing import Any

from syntrop.ir import IRFunction, IRModule, IRNode, IRNodeType, ProbeResult


@dataclass
class IntercalInstruction:
    """A simplified INTERCAL-like instruction."""

    opcode: str
    operands: list[str] = field(default_factory=list)
    label: str = ""
    come_from: str = ""  # COME FROM target label
    probability: float = 1.0  # 1.0 = always, 0.5 = 50% chance
    comment: str = ""


class IntercalBackend:
    """INTERCAL backend compiler for Syntrop IR.

    Compiles IR into a simplified INTERCAL-like representation and
    simulates execution with nondeterministic COME FROM control flow.
    """

    name = "intercal"
    description = "INTERCAL backend with random COME FROM control flow"

    def __init__(self, come_from_probability: float = 0.1, seed: int | None = None) -> None:
        """Initialize the INTERCAL backend.

        Args:
            come_from_probability: Probability that a COME FROM will redirect
                control flow at any given point.
            seed: Random seed for reproducibility.
        """
        self.come_from_probability = come_from_probability
        self.seed = seed
        self._rng = random.Random(seed)
        self._label_counter = 0

    def _next_label(self) -> str:
        """Generate a unique INTERCAL-style label."""
        self._label_counter += 1
        return f"L{self._label_counter:03d}"

    def compile_function(self, func: IRFunction) -> list[IntercalInstruction]:
        """Compile an IR function to INTERCAL-like instructions.

        Args:
            func: The IR function to compile.

        Returns:
            List of INTERCAL-like instructions.
        """
        instructions: list[IntercalInstruction] = []
        instructions.append(
            IntercalInstruction(
                opcode="DO",
                operands=[f"READ OUT {func.name}"],
                label=self._next_label(),
                comment=f"Begin function {func.name}",
            )
        )
        self._compile_node(func.body, instructions)
        instructions.append(
            IntercalInstruction(
                opcode="DO",
                operands=["GIVE UP"],
                comment=f"End function {func.name}",
            )
        )
        return instructions

    def _compile_node(
        self, node: IRNode, instructions: list[IntercalInstruction]
    ) -> None:
        """Recursively compile an IR node to INTERCAL instructions."""
        if node.node_type == IRNodeType.BLOCK:
            for child in node.children:
                self._compile_node(child, instructions)

        elif node.node_type == IRNodeType.FOR_EACH:
            var = node.attributes.get("var", "item")
            iterable = node.attributes.get("iterable", "items")
            label = self._next_label()
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"STASH {var} FROM {iterable}"],
                    label=label,
                    comment=f"FOR EACH {var} IN {iterable}",
                )
            )
            # Insert a COME FROM that may redirect execution
            come_label = self._next_label()
            instructions.append(
                IntercalInstruction(
                    opcode="COME_FROM",
                    operands=[come_label],
                    probability=self.come_from_probability,
                    comment="Nondeterministic loop iteration",
                )
            )
            for child in node.children:
                self._compile_node(child, instructions)

        elif node.node_type == IRNodeType.IF:
            condition = node.attributes.get("condition", "TRUE")
            label = self._next_label()
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"ABSTAIN IF NOT {condition}"],
                    label=label,
                    comment=f"IF {condition}",
                )
            )
            for child in node.children:
                self._compile_node(child, instructions)

        elif node.node_type == IRNodeType.ASSIGN:
            var_name = node.attributes.get("name", "x")
            value = node.attributes.get("value", "0")
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"{var_name} <- {value}"],
                    comment=f"ASSIGN {var_name} = {value}",
                )
            )

        elif node.node_type == IRNodeType.RETURN:
            value = node.attributes.get("value", "0")
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"READ OUT {value}"],
                    comment="RETURN",
                )
            )

        elif node.node_type == IRNodeType.MUTATE:
            target = node.attributes.get("target", "x")
            op = node.attributes.get("operation", "MODIFY")
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"{target} {op}"],
                    comment=f"MUTATE {target}",
                )
            )

        elif node.node_type == IRNodeType.ACCUM:
            var_name = node.attributes.get("name", "acc")
            instructions.append(
                IntercalInstruction(
                    opcode="DO",
                    operands=[f"STASH {var_name}"],
                    comment=f"ACCUM {var_name}",
                )
            )
            for child in node.children:
                self._compile_node(child, instructions)

    def compile_module(self, module: IRModule) -> list[IntercalInstruction]:
        """Compile an entire IR module.

        Args:
            module: The IR module to compile.

        Returns:
            List of INTERCAL-like instructions.
        """
        all_instructions: list[IntercalInstruction] = []
        all_instructions.append(
            IntercalInstruction(
                opcode="DO",
                operands=["READ OUT HEADER"],
                comment=f"Module: {module.name}",
            )
        )
        for func in module.functions:
            func_instrs = self.compile_function(func)
            all_instructions.extend(func_instrs)
        return all_instructions

    def format_intercal(self, instructions: list[IntercalInstruction]) -> str:
        """Format instructions as pseudo-INTERCAL source code.

        Args:
            instructions: List of INTERCAL-like instructions.

        Returns:
            Formatted pseudo-INTERCAL source code string.
        """
        lines = []
        for instr in instructions:
            parts = []
            if instr.label:
                parts.append(f"({instr.label})")
            if instr.probability < 1.0:
                pct = int(instr.probability * 100)
                parts.append(f"DO %{pct}")
            else:
                parts.append(instr.opcode)
            parts.append(" ".join(instr.operands))
            if instr.come_from:
                parts.append(f"COME FROM ({instr.come_from})")
            if instr.comment:
                parts.append(f"  * {instr.comment}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def simulate_execution(
        self, instructions: list[IntercalInstruction], input_data: Any = None
    ) -> dict[str, Any]:
        """Simulate execution of INTERCAL-like instructions.

        This is a simplified simulation that models the key INTERCAL
        semantic: nondeterministic COME FROM control flow.

        Args:
            instructions: List of INTERCAL-like instructions.
            input_data: Optional input data for the program.

        Returns:
            Dictionary with execution results and any divergences.
        """
        rng = random.Random(self.seed)
        pc = 0
        output: list[Any] = []
        variables: dict[str, Any] = {}
        divergences: list[dict[str, Any]] = []
        steps = 0
        max_steps = 10000

        while 0 <= pc < len(instructions) and steps < max_steps:
            instr = instructions[pc]
            steps += 1

            # Check for COME FROM redirection
            if instr.opcode == "COME_FROM":
                if rng.random() < instr.probability:
                    target_label = instr.operands[0] if instr.operands else ""
                    if target_label:
                        # Find the target instruction
                        for i, other in enumerate(instructions):
                            if other.label == target_label and i != pc:
                                divergences.append(
                                    {
                                        "type": "come_from_redirect",
                                        "from_pc": pc,
                                        "to_pc": i,
                                        "label": target_label,
                                    }
                                )
                                pc = i
                                break
                        else:
                            pc += 1
                    else:
                        pc += 1
                else:
                    pc += 1
                continue

            # Handle normal instructions
            if "GIVE UP" in " ".join(instr.operands):
                break
            elif "READ OUT" in " ".join(instr.operands):
                output.append(variables.copy())
            elif "<-" in " ".join(instr.operands):
                # Assignment
                parts = " ".join(instr.operands).split("<-")
                if len(parts) == 2:
                    var_name = parts[0].strip()
                    variables[var_name] = f"value_of_{parts[1].strip()}"

            pc += 1

        return {
            "output": output,
            "variables": variables,
            "divergences": divergences,
            "steps": steps,
            "came_from_triggered": len(divergences),
        }

    def run(self, module: IRModule, input_data: Any = None) -> ProbeResult:
        """Compile and simulate an IR module through the INTERCAL backend.

        Args:
            module: The IR module to process.
            input_data: Optional input data.

        Returns:
            ProbeResult describing any divergences found.
        """
        instructions = self.compile_module(module)
        intercal_source = self.format_intercal(instructions)
        result = self.simulate_execution(instructions, input_data)

        if result["divergences"]:
            descriptions = []
            for div in result["divergences"]:
                descriptions.append(
                    f"COME FROM redirected execution from instruction {div['from_pc']} "
                    f"to instruction {div['to_pc']} (label {div['label']})"
                )
            explanation = (
                "INTERCAL's COME FROM caused nondeterministic control flow. "
                "This reveals that the code assumes deterministic execution order. "
                "Divergences: " + "; ".join(descriptions)
            )
            return ProbeResult(
                probe_name="intercal-backend",
                original_output=None,
                probed_output=result,
                diverged=True,
                divergence_type="control-flow-nondeterminism",
                explanation=explanation,
                severity="warning",
                metadata={
                    "intercal_source": intercal_source,
                    "came_from_count": result["came_from_triggered"],
                },
            )

        return ProbeResult(
            probe_name="intercal-backend",
            original_output=None,
            probed_output=result,
            diverged=False,
            divergence_type="",
            explanation="No divergences detected in INTERCAL simulation",
            severity="info",
            metadata={"intercal_source": intercal_source},
        )
