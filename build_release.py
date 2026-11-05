import os
import shutil
import subprocess
import sys
from pathlib import Path

from Cython.Build import cythonize
from setuptools import Extension, Distribution

HERE = Path(__file__).parent
SRC_DIR = HERE / "src"
BUILD_DIR = HERE / "build_temp"
OUTPUT_DIR = HERE / "src_clean"

SCRIPTS = ["pipeline.py", "metadata.py", "gui.py"]


def build_pyd():
    extensions = []
    for name in SCRIPTS:
        py_path = SRC_DIR / name
        mod_name = f"src.{py_path.stem}"
        temp_dir = BUILD_DIR / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        c_file = temp_dir / (py_path.stem + ".c")
        subprocess.run(
            [sys.executable, "-m", "cython", "-3", str(py_path), "-o", str(c_file)],
            check=True, cwd=str(HERE),
        )

        shutil.copy2(py_path, temp_dir / name)

        ext = Extension(
            mod_name,
            sources=[str(c_file)],
            extra_compile_args=["/O2", "/GL"] if sys.platform == "win32" else ["-O2"],
        )
        extensions.append(ext)

    dist = Distribution({
        "name": "_loy_bear_build",
        "ext_modules": cythonize(
            extensions,
            compiler_directives={
                "language_level": "3",
                "boundscheck": False,
                "wraparound": False,
            },
        ),
        "script_args": ["build_ext", "--build-lib", str(OUTPUT_DIR)],
    })
    dist.parse_command_line()
    dist.run_commands()

    build_ext = dist.get_command_obj("build_ext")
    for name in SCRIPTS:
        stem = Path(name).stem
        # Ask the configured compiler for this module's exact ABI-specific
        # output. Prefix globs may also match unrelated modules or stale builds
        # for another interpreter and silently publish the wrong binary.
        extension = Path(build_ext.get_ext_fullpath(f"src.{stem}"))
        dest = SRC_DIR / f"{stem}{extension.suffix}"
        shutil.copy2(extension, dest)

    for name in SCRIPTS:
        py_file = SRC_DIR / name
        bak = SRC_DIR / (name + ".bak")
        if py_file.exists() and not bak.exists():
            py_file.rename(bak)

    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    print("Backend compiled to .pyd. Source files backed up as .bak.")


def restore_source():
    for name in SCRIPTS:
        bak = SRC_DIR / (name + ".bak")
        py_file = SRC_DIR / name
        stem = Path(name).stem
        for suffix in (".pyd", ".so"):
            # build_pyd normalizes ABI-tagged build outputs to bare names.
            (SRC_DIR / f"{stem}{suffix}").unlink(missing_ok=True)
            for p in SRC_DIR.glob(f"{stem}.*{suffix}"):
                p.unlink(missing_ok=True)
        if bak.exists() and not py_file.exists():
            bak.rename(py_file)
    print("Restored source files.")


if __name__ == "__main__":
    if "--restore" in sys.argv:
        restore_source()
    else:
        build_pyd()
