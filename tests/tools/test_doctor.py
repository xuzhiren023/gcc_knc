"""S0-01: required tools fail usefully; optional test tools may be absent."""
import contextlib
import io
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
doctor = runpy.run_path(str(ROOT / "tools" / "doctor"))


class Doctor(unittest.TestCase):
    def check(self, required, startup=True, missing_directory=None,
              outside=None, missing_file=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sysroot/usr/include").mkdir(parents=True)
            (root / "sysroot/lib64").mkdir()
            for relative in ("lib", "usr/lib"):
                if relative != missing_directory:
                    (root / "sysroot" / relative).mkdir()
            if startup:
                (root / "sysroot/usr/lib64").mkdir()
                for name in ("crt1.o", "crti.o", "crtn.o", "libc.so", "libc_nonshared.a",
                             "Scrt1.o", "gcrt1.o", "Mcrt1.o", "libpthread_nonshared.a",
                             "libm.so", "libpthread.so", "libdl.so", "librt.so",
                             "libcrypt.so", "libutil.so", "libresolv.so", "libnsl.so",
                             "libanl.so", "libthread_db.so"):
                    if name != missing_file:
                        (root / "sysroot/usr/lib64" / name).touch()
            manifest = {"sysroot": "sysroot", "tools": [
                {"name": "gcc", "path": "gcc", "version": "14.4.0",
                 "role": "host compiler", "required": True},
                {"name": "expect", "path": "expect", "version": None,
                 "role": "optional test driver", "required": required}]}
            (root / "gcc").touch()
            if outside is not None:
                manifest["tools"].append({"name": "k1om-mpss-linux-gcc",
                    "path": "cross-gcc", "version": "5.1.1", "role": "donor"})
                (root / "cross-gcc").touch()

            def response(command, **kwargs):
                query = command[-1]
                if query.startswith("-print-"):
                    value = root / ("sysroot" if query == "-print-sysroot" else "bin/tool")
                    if query == outside:
                        value = root.parent / "foreign-toolchain" / "tool"
                    return subprocess.CompletedProcess(command, 0, str(value) + "\n")
                return subprocess.CompletedProcess(command, 0, "gcc 14.4.0 5.1.1\n")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch("subprocess.run") as run:
                run.side_effect = response
                result = doctor["check"](manifest, root)
                if outside is None:
                    run.assert_called_once()
            return result, output.getvalue()

    def test_optional_absence_reports_version_and_succeeds(self):
        result, output = self.check(False)
        self.assertEqual(result, 0)
        self.assertIn("14.4.0", output)
        self.assertIn("ABSENT expect", output)

    def test_required_absence_fails_with_tool_and_path(self):
        result, output = self.check(True)
        self.assertNotEqual(result, 0)
        self.assertIn("MISSING expect", output)
        self.assertIn("expect", output)

    def test_missing_startup_object_fails_with_path(self):
        result, output = self.check(False, startup=False)
        self.assertNotEqual(result, 0)
        self.assertIn("usr/lib64/crt1.o", output.replace("\\", "/"))

    def test_missing_search_parent_fails_with_path(self):
        for relative in ("lib", "usr/lib"):
            with self.subTest(directory=relative):
                result, output = self.check(False, missing_directory=relative)
                self.assertNotEqual(result, 0)
                self.assertIn("sysroot/" + relative, output.replace("\\", "/"))

    def test_compiler_paths_must_stay_in_shared_toolchain(self):
        for query in ("-print-prog-name=as", "-print-prog-name=ld", "-print-sysroot"):
            with self.subTest(query=query):
                result, output = self.check(False, outside=query)
                self.assertNotEqual(result, 0)
                self.assertIn(query, output)
                self.assertIn("outside shared toolchain", output)

    def test_shared_compiler_paths_succeed(self):
        result, output = self.check(False, outside="")
        self.assertEqual(result, 0)
        for query in ("-print-prog-name=as", "-print-prog-name=ld", "-print-sysroot"):
            self.assertIn(query, output)

    def test_missing_development_files_name_recreation_step(self):
        for name in ("crti.o", "crtn.o", "libc.so", "libc_nonshared.a",
                     "Scrt1.o", "gcrt1.o", "Mcrt1.o", "libpthread_nonshared.a"):
            with self.subTest(name=name):
                result, output = self.check(False, missing_file=name)
                self.assertNotEqual(result, 0)
                self.assertIn(name, output)
                self.assertIn("tools/toolchain.py sysroot", output)

    def test_missing_development_link_names_sysroot_step(self):
        for library in ("m", "pthread", "dl", "rt", "crypt", "util", "resolv",
                        "nsl", "anl", "thread_db"):
            name = "lib" + library + ".so"
            with self.subTest(name=name):
                result, output = self.check(False, missing_file=name)
                self.assertNotEqual(result, 0)
                self.assertIn("usr/lib64/" + name, output.replace("\\", "/"))
                self.assertIn("tools/toolchain.py sysroot", output)


if __name__ == "__main__":
    unittest.main()
