"""S13-05: validate the machine parameters and project skill on the host.

Run with tools/run.py and Python with PyYAML installed. The machine file is a
mapping of parameter names to records with an explicit value (null if unknown).
This checks the artifact contract, not the truth of a cited hardware claim.
"""
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[2]
MACHINE = ROOT / "docs/research/knc-machine.yaml"
REFERENCES = ROOT / "docs/research/knc-references.md"
SKILL = ROOT / ".claude/skills/model-first/SKILL.md"
REFERENCE_ID = re.compile(r"\bR\d+[a-z]?\b")


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not silently discard a parameter or field with a duplicate key."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise yaml.constructor.ConstructorError(
                    "duplicate mapping key", node.start_mark,
                    str(key), key_node.start_mark)
            result[key] = self.construct_object(value_node, deep=deep)
        return result


class ModelFirstArtifacts(unittest.TestCase):
    def read_required(self, path):
        self.assertTrue(path.is_file(), "missing required artifact: " + str(path))
        return path.read_text(encoding="utf-8")

    def nonempty_text(self, value, label):
        self.assertIsInstance(value, str, label)
        self.assertTrue(value.strip(), label)

    def test_machine_and_skill(self):
        with self.subTest(artifact="knc-machine.yaml"):
            text = self.read_required(MACHINE)
            parameters = yaml.load(text, Loader=UniqueKeyLoader)
            self.assertIsInstance(parameters, dict)
            self.assertTrue(parameters, "machine parameters must not be empty")
            populated = 0
            for name, parameter in parameters.items():
                with self.subTest(parameter=name):
                    self.nonempty_text(name, "parameter name")
                    self.assertIsInstance(parameter, dict, name)
                    self.assertIn("value", parameter, name)
                    if parameter["value"] in (None, "", [], {}):
                        self.nonempty_text(parameter.get("note"), name + ": unknown-value note")
                        continue
                    populated += 1
                    self.nonempty_text(parameter.get("unit"), name + ": unit")
                    self.assertIn(parameter.get("scope"), ("thread", "core", "card"), name)
                    self.assertIn(parameter.get("evidence"), ("V", "R", "E"), name)
                    self.nonempty_text(parameter.get("source"), name + ": source")
            self.assertGreater(populated, 0, "machine file has no sourced values")
            index = self.read_required(REFERENCES)
            known = set(re.findall(r"^\|\s*(R\d+[a-z]?)\s*\|", index, re.MULTILINE))
            # The index explicitly permits bare group IDs for suffixed entries.
            known.update(re.sub(r"[a-z]$", "", source) for source in tuple(known))
            self.assertTrue(known, "reference index has no R-number rows")
            unknown = set(REFERENCE_ID.findall(text)) - known
            self.assertFalse(unknown, "R-numbers absent from index: " + ", ".join(sorted(unknown)))

        with self.subTest(artifact="SKILL.md"):
            lines = self.read_required(SKILL).splitlines()
            self.assertTrue(lines, "skill must not be empty")
            self.assertEqual(lines[0], "---", "skill must start with YAML frontmatter")
            self.assertIn("---", lines[1:], "frontmatter needs a closing delimiter")
            end = lines.index("---", 1)
            frontmatter = yaml.load("\n".join(lines[1:end]), Loader=UniqueKeyLoader)
            self.assertIsInstance(frontmatter, dict)
            self.assertEqual(frontmatter.get("name"), "model-first")
            self.nonempty_text(frontmatter.get("description"), "skill trigger description")


if __name__ == "__main__":
    unittest.main()
