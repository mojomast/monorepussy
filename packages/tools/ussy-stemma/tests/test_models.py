"""Tests for the models module."""

from stemma.models import (
    ArchetypeResult,
    Classification,
    CollationResult,
    ContaminationReport,
    Reading,
    StemmaNode,
    StemmaTree,
    VariantType,
    VariationUnit,
    Witness,
    WitnessRole,
    normalize_line,
)


class TestNormalizeLine:
    def test_strips_trailing_whitespace(self):
        assert normalize_line("  foo bar  ") == "foo bar"

    def test_strips_inline_comment(self):
        assert normalize_line("x = 1  # comment") == "x = 1"

    def test_preserves_hash_in_string(self):
        # Simple split — the first # is treated as comment start
        result = normalize_line('s = "hello # world"  # real comment')
        assert "# real comment" not in result

    def test_empty_line(self):
        assert normalize_line("") == ""

    def test_only_whitespace(self):
        assert normalize_line("   ") == ""

    def test_normalizes_multiple_spaces(self):
        assert normalize_line("x  =   1") == "x = 1"


class TestWitness:
    def test_basic_creation(self):
        w = Witness(label="A", source="test.py", lines=["x = 1", "y = 2"])
        assert w.label == "A"
        assert w.source == "test.py"
        assert len(w.lines) == 2

    def test_normalized_lines_auto_computed(self):
        w = Witness(label="A", source="test.py", lines=["x = 1  # comment", "y = 2"])
        assert "comment" not in w.normalized_lines[0]
        assert w.normalized_lines[1] == "y = 2"

    def test_empty_witness(self):
        w = Witness(label="A", source="test.py", lines=[])
        assert w.normalized_lines == []


class TestReading:
    def test_basic_reading(self):
        r = Reading(text="if charge > 0:", witnesses=["A", "B"])
        assert r.witness_count == 2
        assert r.witness_labels == "A B"

    def test_variant_type(self):
        r = Reading(text="x = 1", witnesses=["A"], variant_type=VariantType.MAJORITY)
        assert r.variant_type == VariantType.MAJORITY

    def test_default_variant_type(self):
        r = Reading(text="x = 1", witnesses=["A"])
        assert r.variant_type == VariantType.UNANIMOUS


class TestVariationUnit:
    def test_is_variant_single_reading(self):
        r = Reading(text="x = 1", witnesses=["A", "B", "C"])
        unit = VariationUnit(line_number=1, readings=[r])
        assert not unit.is_variant

    def test_is_variant_multiple_readings(self):
        r1 = Reading(text="x = 1", witnesses=["A", "B"])
        r2 = Reading(text="x = 2", witnesses=["C"])
        unit = VariationUnit(line_number=1, readings=[r1, r2])
        assert unit.is_variant

    def test_majority_reading(self):
        r1 = Reading(text="x = 1", witnesses=["A", "B", "C"])
        r2 = Reading(text="x = 2", witnesses=["D"])
        unit = VariationUnit(line_number=1, readings=[r1, r2])
        assert unit.majority_reading == r1

    def test_minority_readings(self):
        r1 = Reading(text="x = 1", witnesses=["A", "B", "C"])
        r2 = Reading(text="x = 2", witnesses=["D"])
        unit = VariationUnit(line_number=1, readings=[r1, r2])
        assert unit.minority_readings == [r2]

    def test_empty_readings(self):
        unit = VariationUnit(line_number=1, readings=[])
        assert unit.majority_reading is None
        assert unit.minority_readings == []


class TestCollationResult:
    def test_empty_collation(self):
        c = CollationResult()
        assert c.total_lines == 0
        assert c.variant_count == 0
        assert c.unanimous_count == 0

    def test_variant_counts(self):
        r1 = Reading(text="x = 1", witnesses=["A", "B"])
        r2 = Reading(text="x = 2", witnesses=["C"])
        v1 = VariationUnit(line_number=1, readings=[r1, r2])  # variant
        v2 = VariationUnit(line_number=2, readings=[Reading(text="y = 1", witnesses=["A", "B", "C"])])  # unanimous

        c = CollationResult(
            witnesses=[Witness(label="A", source="a.py"), Witness(label="B", source="b.py"), Witness(label="C", source="c.py")],
            variation_units=[v1, v2],
            aligned_lines={0: {"A": "x=1", "B": "x=1", "C": "x=2"}, 1: {"A": "y=1", "B": "y=1", "C": "y=1"}},
        )
        assert c.variant_count == 1
        assert c.unanimous_count == 1
        assert c.total_lines == 2


class TestStemmaNode:
    def test_basic_creation(self):
        node = StemmaNode(label="A", role=WitnessRole.TERMINAL)
        assert node.label == "A"
        assert node.role == WitnessRole.TERMINAL
        assert node.children == []

    def test_add_child(self):
        parent = StemmaNode(label="α", role=WitnessRole.ARCHETYPE)
        child = StemmaNode(label="A", role=WitnessRole.TERMINAL)
        parent.add_child(child)
        assert child in parent.children
        assert child.parent is parent


class TestStemmaTree:
    def test_empty_tree(self):
        tree = StemmaTree()
        assert tree.root is None
        assert tree.terminal_nodes == []
        assert tree.archetype is None

    def test_find_node(self):
        node = StemmaNode(label="A", role=WitnessRole.TERMINAL)
        tree = StemmaTree(nodes=[node])
        assert tree.find_node("A") is node
        assert tree.find_node("Z") is None

    def test_terminal_nodes(self):
        t1 = StemmaNode(label="A", role=WitnessRole.TERMINAL)
        t2 = StemmaNode(label="B", role=WitnessRole.TERMINAL)
        root = StemmaNode(label="α", role=WitnessRole.ARCHETYPE, children=[t1, t2])
        tree = StemmaTree(root=root, nodes=[root, t1, t2])
        assert len(tree.terminal_nodes) == 2

    def test_archetype_property(self):
        root = StemmaNode(label="α", role=WitnessRole.ARCHETYPE)
        tree = StemmaTree(root=root, nodes=[root])
        assert tree.archetype is root


class TestArchetypeResult:
    def test_basic_creation(self):
        result = ArchetypeResult(
            lines=["x = 1", "y = 2"],
            annotations={2: "Majority reading"},
            confidence=0.85,
        )
        assert len(result.lines) == 2
        assert result.confidence == 0.85
        assert result.method == "Lachmannian"


class TestContaminationReport:
    def test_basic_creation(self):
        report = ContaminationReport(
            witness="D",
            primary_lineage="γ",
            contaminating_source="β",
        )
        assert report.witness == "D"
        assert report.primary_lineage == "γ"


class TestEnums:
    def test_variant_type_values(self):
        assert VariantType.UNANIMOUS.value == "unanimous"
        assert VariantType.MAJORITY.value == "majority"
        assert VariantType.VARIANT.value == "variant"
        assert VariantType.OMISSION.value == "omission"

    def test_classification_values(self):
        assert Classification.SCRIBAL_ERROR.value == "scribal_error"
        assert Classification.CONSCIOUS_MODIFICATION.value == "conscious_modification"
        assert Classification.AMBIGUOUS.value == "ambiguous"

    def test_witness_role_values(self):
        assert WitnessRole.ARCHETYPE.value == "archetype"
        assert WitnessRole.HYPERARCHETYPE.value == "hyparchetype"
        assert WitnessRole.TERMINAL.value == "terminal"
        assert WitnessRole.CONTAMINATED.value == "contaminated"
