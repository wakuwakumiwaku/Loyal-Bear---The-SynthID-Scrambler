"""Exercise exact native release output selection using one tiny Cython module."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_output", ROOT / "build_release.py")
assert SPEC is not None and SPEC.loader is not None
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
assert Path(release.__file__).resolve() == ROOT / "build_release.py"


@unittest.skipUnless(os.name == "posix", "Native regression requires a POSIX C compiler")
class ReleaseOutputTests(unittest.TestCase):
    def test_only_compiler_selected_extension_is_published(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            src = root / "src"
            src.mkdir()
            (src / "__init__.py").write_text("")
            (src / "pipeline.py").write_text("def value():\n    return 42\n")
            canary = src / "pipeline_extra.so"
            canary.write_bytes(b"existing unrelated source-tree extension")
            output = root / "src_clean"
            compiled_bytes = []
            original_run = release.Distribution.run_commands
            def compile_with_sidecars(dist):
                original_run(dist)  # actual Cython/native compilation
                build = dist.get_command_obj("build_ext")
                exact = Path(build.get_ext_fullpath("src.pipeline"))
                compiled_bytes.append(exact.read_bytes())
                # Build output directories can contain other modules or outputs
                # left by another ABI. Neither is the requested build output.
                (output / "src/pipeline_extra.so").write_bytes(b"unrelated extension output")
                (output / "src/pipeline.cpython-000-obsolete.so").write_bytes(b"stale ABI output")
            previous = Path.cwd()
            try:
                os.chdir(root)
                with mock.patch.multiple(release, HERE=root, SRC_DIR=src,
                                         BUILD_DIR=root / "build_temp", OUTPUT_DIR=output,
                                         SCRIPTS=["pipeline.py"]), \
                     mock.patch.object(release.Distribution, "run_commands", compile_with_sidecars):
                    release.build_pyd()
                published = src / "pipeline.so"
                self.assertEqual(published.read_bytes(), compiled_bytes[0],
                                 "Publish exactly the extension selected by build_ext, not a prefix/ABI glob match")
                self.assertEqual(canary.read_bytes(), b"existing unrelated source-tree extension")
                self.assertTrue((src / "pipeline.py.bak").exists())
                self.assertFalse((src / "pipeline.py").exists())
                check = subprocess.run([sys.executable, "-B", "-c",
                                        "from src import pipeline; assert pipeline.value() == 42; print(pipeline.__file__)"],
                                       cwd=root, capture_output=True, text=True, timeout=10,
                                       env=dict(os.environ, PYTHONPATH=str(root)))
                self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
                self.assertIn(str(published), check.stdout)
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
