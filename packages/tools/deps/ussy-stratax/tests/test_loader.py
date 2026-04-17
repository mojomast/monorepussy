"""Tests for probe YAML loader."""
import os
import tempfile
import pytest
from strata.probes.loader import ProbeLoader


class TestProbeLoader:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.loader = ProbeLoader(probe_dirs=[])

    def _write_yaml(self, name, content):
        path = os.path.join(self.tmpdir, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_load_file(self):
        path = self._write_yaml("test.yaml", """
package: json
function: dumps
probes:
  - name: json_dumps_list
    input:
      obj: [1, 2, 3]
    output: "[1, 2, 3]"
    returns_type: str
  - name: json_dumps_dict
    input:
      obj:
        key: value
    returns_type: str
""")
        probes = self.loader.load_file(path)
        assert len(probes) == 2
        assert probes[0].name == "json_dumps_list"
        assert probes[0].package == "json"
        assert probes[0].function == "dumps"
        assert probes[1].name == "json_dumps_dict"

    def test_load_empty_file(self):
        path = self._write_yaml("empty.yaml", "")
        probes = self.loader.load_file(path)
        assert len(probes) == 0

    def test_load_dir(self):
        self._write_yaml("a.yaml", """
package: pkg_a
function: fn_a
probes:
  - name: probe_a
""")
        self._write_yaml("b.yaml", """
package: pkg_b
function: fn_b
probes:
  - name: probe_b
""")
        probes = self.loader.load_dir(self.tmpdir)
        assert len(probes) == 2

    def test_load_dir_nonexistent(self):
        probes = self.loader.load_dir("/nonexistent/dir")
        assert len(probes) == 0

    def test_load_for_package(self):
        loader = ProbeLoader(probe_dirs=[self.tmpdir])
        self._write_yaml("test.yaml", """
package: target_pkg
function: fn
probes:
  - name: target_probe
""")
        self._write_yaml("other.yaml", """
package: other_pkg
function: fn
probes:
  - name: other_probe
""")
        probes = loader.load_for_package("target_pkg")
        assert len(probes) == 1
        assert probes[0].name == "target_probe"

    def test_parse_yaml_string(self):
        yaml_str = """
package: mypkg
function: myfn
probes:
  - name: test_probe
    returns_type: dict
"""
        probes = ProbeLoader.parse_yaml_string(yaml_str)
        assert len(probes) == 1
        assert probes[0].name == "test_probe"
        assert probes[0].returns_type == "dict"

    def test_load_all(self):
        loader = ProbeLoader(probe_dirs=[self.tmpdir])
        self._write_yaml("a.yml", """
package: pkg_a
function: fn
probes:
  - name: p1
""")
        probes = loader.load_all()
        assert len(probes) >= 1

    def test_load_with_all_probe_fields(self):
        path = self._write_yaml("full.yaml", """
package: mypkg
function: myfn
probes:
  - name: full_probe
    input: [1, 2, 3]
    output: 6
    output_has_keys: ["result"]
    target_mutated: false
    raises: ValueError
    returns_type: int
    custom_assertion: "check something"
""")
        probes = self.loader.load_file(path)
        assert len(probes) == 1
        p = probes[0]
        assert p.name == "full_probe"
        assert p.input_data == [1, 2, 3]
        assert p.expected_output == 6
        assert p.output_has_keys == ["result"]
        assert p.raises == "ValueError"
        assert p.returns_type == "int"
