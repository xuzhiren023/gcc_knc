"""S14-42 artifact contract; run through tools/run.py with standard-library Python.

This checks structure and citations, not the truth of a hardware claim. Card
evidence may cite a repository document by its unique basename, without making
the installed skill depend on the GCC-KNC checkout. Markdown file links must
stay inside the copied skill. Vendor text is read only for the overlap check;
failure messages never reproduce a matching vendor passage.
"""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from test_model_first import load_yaml_subset


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "skills/knc-optimize"
SHARED = (ROOT.parent / "_shared" if ROOT.parent.name == ".work"
          else ROOT / ".work/_shared")
REQUIRED = (
    "SKILL.md", "references/practices.md", "references/machine.md",
    "references/pitfalls.md", "references/example.md", "scripts/install.sh",
)
CORPUS = {
    "R01": SHARED / "knc-refs/ssdg-2012.txt",
    "R16": SHARED / "knc-refs/klemm-optimization-2013.txt",
    "R27": SHARED / "intel-327364-001-xeon-phi-isa.txt",
}
VERDICTS = {"confirmed", "contradicted", "untested",
            "not applicable to GCC-KNC"}
INLINE_LINK = re.compile(r"!?\[[^\]\n]*\]\(([^)\n]+)\)")
REFERENCE_DEF = re.compile(r"^ {0,3}\[([^\]]+)\]:\s*(\S+).*$", re.M)
REFERENCE_USE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
FILE_CITATION = re.compile(
    r"(?<![\w./-])([\w-]+\.(?:md|yaml|yml|json|csv|tsv|txt|log))\b")


def words(text):
    # Join PDF line-end hyphenation before ignoring punctuation and case.
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    return re.findall(r"[a-z0-9]+", text.casefold())


def ngrams(tokens, length=12):
    for index in range(len(tokens) - length + 1):
        yield tuple(tokens[index:index + length])


def table_rows(text):
    """Read pipe tables; do not silently discard malformed practice rows."""
    header = None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.lstrip().startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in re.split(r"(?<!\\)\|", line.strip())[1:-1]]
        if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if header is None:
            header = [cell.casefold() for cell in cells]
        else:
            yield number, header, cells


def heading_anchors(text):
    anchors, counts = set(), {}
    for heading in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", text, re.M):
        slug = re.sub(r"[^\w\- ]", "", heading.casefold()).replace(" ", "-")
        count = counts.get(slug, 0)
        anchors.add(slug + ("-" + str(count) if count else ""))
        counts[slug] = count + 1
    anchors.update(re.findall(r'(?:id|name)=[\"\']([^\"\']+)[\"\']', text))
    return anchors


class KncOptimizeSkill(unittest.TestCase):
    def required_text(self, relative):
        path = SKILL / relative
        self.assertTrue(path.is_file(), "missing required skill file: " + relative)
        data = path.read_bytes()
        self.assertTrue(data.strip(), "empty skill file: " + relative)
        self.assertNotIn(b"\r", data, "skill files must use LF: " + relative)
        self.assertTrue(data.isascii(), "skill files must be ASCII: " + relative)
        return data.decode("ascii")

    def skill_files(self):
        self.assertTrue(SKILL.is_dir(), "missing skills/knc-optimize")
        files = sorted(path for path in SKILL.rglob("*") if path.is_file())
        self.assertTrue(files, "skill directory is empty")
        return files

    def test_required_artifacts(self):
        for relative in REQUIRED:
            with self.subTest(file=relative):
                self.required_text(relative)
        method = ROOT / "docs/research/knc-optimize-method.md"
        self.assertTrue(method.is_file(), "missing source recheck research table")
        self.assertTrue(method.read_text(encoding="utf-8").strip())

    def test_frontmatter(self):
        lines = self.required_text("SKILL.md").splitlines()
        self.assertEqual(lines[0], "---", "frontmatter must be first")
        self.assertIn("---", lines[1:], "missing frontmatter closing delimiter")
        end = lines.index("---", 1)
        metadata = load_yaml_subset("\n".join(lines[1:end]))
        self.assertEqual(metadata.get("name"), "knc-optimize")
        description = metadata.get("description")
        self.assertIsInstance(description, str)
        self.assertRegex(description.casefold(), r"optimi[sz]e|tun(?:e|ing)|speed up")
        for trigger in ("xeon phi", "knc", "mic", "k1om", "imci"):
            self.assertRegex(description.casefold(), r"\b" + trigger + r"\b")

    def test_practice_sources_and_verdicts(self):
        text = self.required_text("references/practices.md")
        rows = list(table_rows(text))
        self.assertTrue(rows, "practices must contain nonempty table rows")
        evidence_files = {}
        for directory in (ROOT / "docs", ROOT / "tests"):
            for path in directory.rglob("*"):
                if path.is_file():
                    evidence_files.setdefault(path.name, []).append(path)
        for number, header, cells in rows:
            with self.subTest(line=number):
                self.assertEqual(len(cells), len(header), "malformed practice row")
                source_columns = [i for i, name in enumerate(header) if "source" in name]
                verdict_columns = [i for i, name in enumerate(header)
                                   if "verdict" in name or "status" in name]
                self.assertEqual(len(source_columns), 1, "need a Source locator column")
                self.assertEqual(len(verdict_columns), 1, "need a Card verdict column")
                source = cells[source_columns[0]]
                self.assertRegex(source, r"\bR\d{2}[a-z]?\b", "missing source ID")
                self.assertRegex(
                    source, r"(?i)\b(?:p(?:p)?\.\s*\d+|slides?\s+\d+|"
                    r"sections?\s+\S+|GUID-[A-F0-9-]+|heading\s+\S+)",
                    "missing page, slide, section or HTML locator")
                verdict = cells[verdict_columns[0]].strip(" *`")
                # Explanations and citations may follow the verdict in its cell.
                matches = [value for value in VERDICTS
                           if re.match(re.escape(value) + r"(?:$|[\s:;(,.])", verdict)]
                self.assertEqual(len(matches), 1, "use one of the four ticket verdicts")
                if matches[0] in ("confirmed", "contradicted"):
                    evidence = " ".join(cell for i, cell in enumerate(cells)
                                        if i != source_columns[0])
                    cited = FILE_CITATION.findall(evidence)
                    self.assertTrue(cited, "card verdict needs a file citation")
                    for name in cited:
                        self.assertEqual(len(evidence_files.get(name, [])), 1,
                                         "card evidence missing or ambiguous: " + name)

    def test_portable_paths(self):
        for path in self.skill_files():
            with self.subTest(file=path.relative_to(SKILL).as_posix()):
                text = self.required_text(path.relative_to(SKILL).as_posix())
                normalized = text.replace("\\", "/")
                self.assertNotRegex(normalized, r"(?i)gcc_knc[/]|[a-z]:/|/cygdrive/")
                self.assertNotRegex(normalized, r"(?<![\w-])(?:\.work/|docs/research/)")
                self.assertNotRegex(normalized, r"(?<![\w-])tools/[\w.-]+")
                for relative in re.findall(r"(?:\.\./)+[\w./-]+", normalized):
                    self.assertTrue((path.parent / relative).resolve().is_relative_to(SKILL.resolve()),
                                    "relative path escapes installed skill: " + relative)

    def check_link(self, document, target):
        # Strip an optional Markdown title; angle brackets delimit spaced URLs.
        target = target.strip()
        target = target[1:target.index(">")] if target.startswith("<") else target.split()[0]
        parsed = urlsplit(target)
        if parsed.scheme:
            self.assertIn(parsed.scheme, ("https", "http", "mailto"), "unsupported link scheme")
            self.assertTrue(parsed.netloc if parsed.scheme != "mailto" else parsed.path)
            return  # No network access: only packaged links are resolved here.
        self.assertFalse(parsed.netloc, "external links must name their scheme")
        destination = (document.parent / unquote(parsed.path)).resolve() if parsed.path else document
        self.assertTrue(destination.is_relative_to(SKILL.resolve()),
                        "link leaves the portable skill: " + target)
        self.assertTrue(destination.is_file(), "broken file link: " + target)
        if parsed.fragment:
            self.assertIn(unquote(parsed.fragment),
                          heading_anchors(destination.read_text(encoding="ascii")),
                          "broken anchor: " + target)

    def test_links_resolve(self):
        for path in self.skill_files():
            if path.suffix != ".md":
                continue
            text = self.required_text(path.relative_to(SKILL).as_posix())
            definitions = {label.casefold(): target
                           for label, target in REFERENCE_DEF.findall(text)}
            targets = INLINE_LINK.findall(text) + list(definitions.values())
            for label, reference in REFERENCE_USE.findall(text):
                key = (reference or label).casefold()
                self.assertIn(key, definitions, "undefined reference link: " + key)
                targets.append(definitions[key])
            for target in targets:
                with self.subTest(file=path.name, link=target):
                    self.check_link(path, target)

    def test_no_vendor_twelve_word_run(self):
        # Missing corpus is an error, never a successful/skip result. Keep the
        # local vendor extractions out of git and out of diagnostic output.
        for source, path in CORPUS.items():
            self.assertTrue(path.is_file(), "missing local extraction for " + source)
            self.assertGreater(path.stat().st_size, 0, "empty extraction for " + source)
        skill_grams = {}
        for path in self.skill_files():
            text = self.required_text(path.relative_to(SKILL).as_posix())
            for gram in ngrams(words(text)):
                skill_grams.setdefault(gram, path.relative_to(SKILL).as_posix())
        self.assertTrue(skill_grams, "skill is too short to exercise the overlap check")
        for source, path in CORPUS.items():
            for gram in ngrams(words(path.read_text(encoding="utf-8"))):
                if gram in skill_grams:
                    self.fail("shared 12-word run: %s and %s (passage withheld)"
                              % (skill_grams[gram], source))


if __name__ == "__main__":
    unittest.main()
