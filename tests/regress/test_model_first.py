"""S13-05: validate the machine parameters and project skill on the host.

Run with tools/run.py and standard-library Python. The machine file is a
mapping of parameter names to records with an explicit value (null if unknown).
This checks the artifact contract, not the truth of a cited hardware claim.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
MACHINE = ROOT / "docs/research/knc-machine.yaml"
REFERENCES = ROOT / "docs/research/knc-references.md"
SKILL = ROOT / ".claude/skills/model-first/SKILL.md"
REFERENCE_ID = re.compile(r"\bR\d+[a-z]?\b")


def unique_mapping(pairs):
    """Reject duplicate keys in both block and flow mappings."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate mapping key: " + key)
        result[key] = value
    return result


def inline_yaml(value, anchors):
    def quote_identifier(match):
        token = match[0]
        if token in ("null", "true", "false"):
            return token
        if token.lower() in ("null", "true", "false", "yes", "no", "on", "off"):
            raise ValueError("unsupported implicit scalar: " + token)
        return json.dumps(token)

    if value.startswith("&"):
        match = re.fullmatch(r"&([a-z_][a-z0-9_]*) (.+)", value)
        if not match or match[1] in anchors:
            raise ValueError("unsupported or duplicate anchor: " + value)
        result = inline_yaml(match[2], anchors)
        anchors[match[1]] = result
        return result
    if value.startswith("*"):
        if value[1:] not in anchors:
            raise ValueError("unknown alias: " + value)
        return anchors[value[1:]]
    if value.startswith(("[", "{")):
        # Quote bare identifiers outside JSON-style strings, then let JSON
        # validate delimiters, commas, scalar syntax and duplicate keys.
        parts = re.findall(r'"(?:[^"\\]|\\.)*"|[^"\x00-\x1f]+', value)
        if "".join(parts) != value:
            raise ValueError("unsupported flow quoting: " + value)
        for index, part in enumerate(parts):
            if part.startswith('"'):
                continue
            if re.search(r":(?=\S|$)", part):
                raise ValueError("flow colons require a following space")
            parts[index] = re.sub(
                r"[A-Za-z_][A-Za-z0-9_-]*",
                quote_identifier, part)
        return json.loads("".join(parts), object_pairs_hook=unique_mapping)
    if (value.startswith('"') or value in ("null", "true", "false")
            or re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value)):
        return json.loads(value)
    if (not re.fullmatch(r"[A-Za-z_][^\[\]{}#\x00-\x1f]*", value)
            or re.search(r":(?:\s|$)", value)
            or value.lower() in ("null", "true", "false", "yes", "no", "on", "off")):
        raise ValueError("unsupported scalar syntax: " + value)
    return value


def load_yaml_subset(text):
    """Read only the YAML forms used by these artifacts, without dependencies.

    Supported: two-space block mappings with identifier keys; single-line flow
    maps/lists; decimal numbers, null, booleans, plain and JSON-quoted strings;
    inline anchors and backward aliases; simple equally indented >- text.
    Blank lines and whole-line comments are allowed outside folded text.
    Other syntax (including tags, merge keys and block sequences) fails loudly.
    """
    if re.search(r"[\x00-\x09\x0b-\x1f\x7f\ufeff]", text):
        raise ValueError("unsupported control character, tab or BOM")
    lines, anchors, root = text.splitlines(), {}, {}
    stack = [(0, root)]
    index = 0
    while index < len(lines):
        line_number = index + 1
        line = lines[index].rstrip()
        index += 1
        if not line or line.lstrip().startswith("#"):
            continue
        try:
            match = re.fullmatch(r"( *)([a-z_][a-z0-9_]*):(?: (.+))?", line)
            if not match:
                raise ValueError("expected a block mapping entry")
            indent, key, value = len(match[1]), match[2], match[3]
            while indent < stack[-1][0]:
                if not stack.pop()[1]:
                    raise ValueError("empty block mapping; use explicit null or {}")
            if indent != stack[-1][0]:
                raise ValueError("expected two-space mapping indentation")
            mapping = stack[-1][1]
            if key in mapping:
                raise ValueError("duplicate mapping key: " + key)
            if value is None:
                mapping[key] = {}
                stack.append((indent + 2, mapping[key]))
            elif value == ">-":
                prefix, folded = " " * (indent + 2), []
                while index < len(lines) and lines[index].startswith(prefix):
                    part = lines[index][len(prefix):].rstrip()
                    if not part or part[0].isspace():
                        raise ValueError("unsupported folded-text indentation or blank line")
                    folded.append(part)
                    index += 1
                if not folded:
                    raise ValueError("empty folded text")
                mapping[key] = " ".join(folded)
            else:
                mapping[key] = inline_yaml(value, anchors)
        except ValueError as error:
            raise ValueError("YAML line %d: %s" % (line_number, error)) from error
    if any(not mapping for _, mapping in stack):
        raise ValueError("empty block mapping; use explicit null or {}")
    return root


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
            parameters = load_yaml_subset(text)
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
            frontmatter = load_yaml_subset("\n".join(lines[1:end]))
            self.assertIsInstance(frontmatter, dict)
            self.assertEqual(frontmatter.get("name"), "model-first")
            self.nonempty_text(frontmatter.get("description"), "skill trigger description")


if __name__ == "__main__":
    unittest.main()
