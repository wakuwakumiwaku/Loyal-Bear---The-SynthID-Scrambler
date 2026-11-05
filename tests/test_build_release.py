"""Release restore tests use synthetic sources, never models or the GUI."""
from contextlib import contextmanager
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_release", ROOT / "build_release.py")
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


@contextmanager
def synthetic_project():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        src = root / "src"
        src.mkdir()
        (src / "__init__.py").write_text("", encoding="utf-8")
        old_cwd = Path.cwd()
        try:
            os.chdir(root)
            with mock.patch.multiple(release, HERE=root, SRC_DIR=src,
                                     BUILD_DIR=root / "build_temp", OUTPUT_DIR=root / "src_clean"):
                yield src
        finally:
            os.chdir(old_cwd)


class RestoreTests(unittest.TestCase):
    def test_restore_removes_exact_and_abi_tagged_artifacts(self):
        with synthetic_project() as src:
            for name in release.SCRIPTS:
                stem = Path(name).stem
                (src / (name + ".bak")).write_text("VALUE = 'source'\n", encoding="utf-8")
                for suffix in (".pyd", ".so", ".cp310-win_amd64.pyd", ".cpython-310-x86_64-linux-gnu.so"):
                    (src / (stem + suffix)).write_bytes(b"synthetic extension")
            unrelated = src / "pipeline_extra.so"
            unrelated.write_bytes(b"keep")
            release.restore_source()
            for name in release.SCRIPTS:
                self.assertEqual((src / name).read_text(encoding="utf-8"), "VALUE = 'source'\n")
                self.assertFalse((src / (Path(name).stem + ".so")).exists(), "Bare .so created by build_pyd must be removed")
                self.assertFalse((src / (Path(name).stem + ".pyd")).exists(), "Bare .pyd created by build_pyd must be removed")
                self.assertEqual(list(src.glob(Path(name).stem + ".*.so")), [])
                self.assertEqual(list(src.glob(Path(name).stem + ".*.pyd")), [])
            self.assertEqual(unrelated.read_bytes(), b"keep")
            release.restore_source()  # idempotent

    def test_existing_source_is_not_overwritten(self):
        with synthetic_project() as src:
            (src / "pipeline.py").write_text("VALUE = 'edited'", encoding="utf-8")
            (src / "pipeline.py.bak").write_text("VALUE = 'backup'", encoding="utf-8")
            release.restore_source()
            self.assertEqual((src / "pipeline.py").read_text(encoding="utf-8"), "VALUE = 'edited'")
            self.assertEqual((src / "pipeline.py.bak").read_text(encoding="utf-8"), "VALUE = 'backup'")

    @unittest.skipUnless(os.name == "posix", "Native compile smoke test runs with the POSIX compiler")
    def test_real_synthetic_build_restore_roundtrip(self):
        with synthetic_project() as src:
            for name in release.SCRIPTS:
                (src / name).write_text("def value():\n    return 42\n", encoding="utf-8")
            release.build_pyd()
            for name in release.SCRIPTS:
                self.assertTrue((src / (Path(name).stem + ".so")).exists())
                self.assertFalse((src / name).exists())
            release.restore_source()
            for name in release.SCRIPTS:
                self.assertTrue((src / name).exists())
                self.assertFalse((src / (Path(name).stem + ".so")).exists(), "Restore must undo the actual release build output")


if __name__ == "__main__":
    unittest.main()
