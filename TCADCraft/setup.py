import os
import platform
import sys
import subprocess
import importlib.util
from pathlib import Path
import numpy as np
from setuptools import setup, Extension
from setuptools.command.build import build as _build
from setuptools.command.build_ext import build_ext as _build_ext
from Cython.Build import cythonize
# PEP 517 hooks need not put the project directory on sys.path. Load the
# adjacent build-only helper explicitly, including when rebuilding an sdist.
_config_spec = importlib.util.spec_from_file_location(
    "_tcad_build_config", Path(__file__).resolve().with_name("tcad_build_config.py")
)
_build_config = importlib.util.module_from_spec(_config_spec)
_config_spec.loader.exec_module(_build_config)
constants_profile = _build_config.constants_profile
build_cache_tag = _build_config.build_cache_tag

# Reject unknown profiles before generating code or probing optional libraries.
selected_constants_profile = constants_profile()

class build(_build):
    """Isolate caches while keeping all wheel commands on the same library root."""
    def finalize_options(self):
        # Distutils does not track compiler definitions. Set the shared build
        # base before deriving build_py/build_ext/install library directories.
        # Changing only build_ext.build_lib nests the extension under the cache
        # tag inside wheels, making the installed tcad.core import fail.
        tag = build_cache_tag(force_long_double, selected_constants_profile)
        self.build_base = os.path.join(self.build_base, tag)
        super().finalize_options()


class build_ext(_build_ext):
    """Custom build_ext that removes duplicate rpaths on macOS."""

    def copy_extensions_to_source(self):
        # A different backend's installed .so can be newer than this backend's
        # cache. Always install the selected library; do not force compilation.
        previous_force = self.force
        try:
            self.force = True
            super().copy_extensions_to_source()
        finally:
            self.force = previous_force

    def run(self):
        super().run()
        if sys.platform == "darwin":
            for ext in self.extensions:
                output = self.get_ext_fullpath(ext.name)
                if os.path.exists(output):
                    self._fix_duplicate_rpaths(output)
    
    def _fix_duplicate_rpaths(self, path):
        try:
            result = subprocess.run(["otool", "-l", path], capture_output=True, text=True)
            seen = set()
            to_remove = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.startswith("path "):
                    rpath = line.split()[1]
                    if rpath in seen:
                        to_remove.append(rpath)
                    else:
                        seen.add(rpath)
            for rpath in to_remove:
                subprocess.run(["install_name_tool", "-delete_rpath", rpath, path],
                               capture_output=True)
        except Exception:
            pass

# Platform detection
is_macos = sys.platform == "darwin"
is_windows = sys.platform == "win32"
machine = platform.machine().lower()
is_arm64 = machine in ("arm64", "aarch64")
use_lapack = os.environ.get("TCAD_USE_LAPACK", "0") == "1"
force_long_double = os.environ.get("TCAD_FORCE_LONG_DOUBLE", "0") == "1"

if is_windows:
    raise RuntimeError(
        "Native Windows builds are not supported because the extended-precision "
        "core requires GCC/Clang; use WSL2 or a Linux build host."
    )

extra_link_args = []
extra_compile_args = ["-std=c++17", "-O3"]
if use_lapack:
    extra_compile_args.append("-DTCAD_USE_LAPACK")
    if os.environ.get("TCAD_LAPACK_ILP64", "0") == "1":
        extra_compile_args.append("-DTCAD_LAPACK_ILP64")

# --- PETSc detection and configuration ---
petsc_available = False
petsc_include_dirs = []
petsc_library_dirs = []
petsc_libs = []

if os.environ.get("TCAD_USE_PETSC", "1") != "0":
    # Check for Homebrew PETSc installation
    petsc_prefix = os.environ.get("PETSC_DIR", "/opt/homebrew/opt/petsc")
    hypre_prefix = os.environ.get("HYPRE_DIR", "/opt/homebrew/opt/hypre")
    mpi_prefix = os.environ.get("MPI_DIR", "/opt/homebrew/Cellar/open-mpi/5.0.9")
    
    petsc_header = os.path.join(petsc_prefix, "include", "petsc.h")
    if not os.path.isfile(petsc_header) and os.path.isfile("/usr/include/petsc/petsc.h"):
        # System-wide PETSc (e.g. Linux package with MPIUNI, no MPI needed)
        petsc_available = True
        petsc_include_dirs = ["/usr/include/petsc"]
        petsc_library_dirs = ["/usr/lib64"]
        petsc_libs = ["petsc"]
        extra_compile_args.append("-DTCAD_USE_PETSC")
    if os.path.isfile(petsc_header):
        petsc_available = True
        petsc_include_dirs = [
            os.path.join(petsc_prefix, "include"),
            os.path.join(hypre_prefix, "include"),
            os.path.join(mpi_prefix, "include"),
        ]
        petsc_library_dirs = [
            os.path.join(petsc_prefix, "lib"),
            os.path.join(hypre_prefix, "lib"),
            os.path.join(mpi_prefix, "lib"),
        ]
        petsc_libs = ["petsc", "mpi"]
        extra_compile_args.append("-DTCAD_USE_PETSC")
        
        # On macOS, PETSc C++ headers require GCC (not Apple Clang)
        # GCC on ARM64 needs -fext-numeric-literals to accept Q suffix literals
        if is_macos:
            os.environ.setdefault("CC", "gcc-15")
            os.environ.setdefault("CXX", "g++-15")
            extra_compile_args.append("-fext-numeric-literals")

# macOS-specific settings
if is_macos:
    extra_compile_args.append("-arch")
    extra_compile_args.append(os.uname().machine)
    
    # SDK path is needed for system C headers (e.g., wchar.h) especially with GCC
    import subprocess
    try:
        sdk_path = subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip()
        extra_compile_args.append("-isysroot")
        extra_compile_args.append(sdk_path)
        # Only add libc++ path when using Apple Clang (not GCC)
        if not petsc_available:
            cpp_include = os.path.join(sdk_path, "usr", "include", "c++", "v1")
            if os.path.isdir(cpp_include):
                extra_compile_args.append("-I" + cpp_include)
    except Exception:
        pass
    
    # Accelerate framework linking skipped when using GCC (PETSc path)
    # Native dense direct solver is self-contained; no BLAS/LAPACK calls
    if not petsc_available and use_lapack:
        extra_link_args.append("-framework")
        extra_link_args.append("Accelerate")
    
    # GCC on macOS needs explicit system library path for linking
    if petsc_available:
        extra_link_args.append("-L/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib")
    
    if not is_arm64 and not force_long_double:
        extra_link_args.append("-lquadmath")
else:
    # Linux / other Unix.  Release wheels are portable by default; developers
    # may opt into host-specific vector instructions for local benchmarking.
    if os.environ.get("TCAD_NATIVE_OPT", "0") == "1":
        extra_compile_args.append("-march=native")
    # GCC needs -fext-numeric-literals to accept __float128 'Q' suffix literals
    extra_compile_args.append("-fext-numeric-literals")
    if not force_long_double:
        extra_link_args.append("-lquadmath")
    if use_lapack:
        extra_link_args.append("-llapack")
        extra_link_args.append("-lblas")

if os.environ.get("TCAD_DEBUG"):
    extra_compile_args = ["-std=c++17", "-O0", "-g", "-fno-omit-frame-pointer"]
    if is_macos:
        extra_compile_args.append("-arch")
        extra_compile_args.append(machine)

if force_long_double:
    extra_compile_args.append("-DTCAD_FORCE_LONG_DOUBLE")

sources = [
    "tcad/core/_bindings.pyx",
    "src/math_types.cpp",
    "src/sparse_matrix.cpp",
    "src/linear_solver.cpp",
    "src/ilu_preconditioner.cpp",
    "src/ic_preconditioner.cpp",
    "src/poisson_solver.cpp",
    "src/density_gradient.cpp",
    "src/gummel_solver.cpp",
    "src/newton_solver.cpp",
    "src/mobility_model.cpp",
    "src/device_simulator.cpp",
    "src/device_simulator_double.cpp",
]

if petsc_available:
    sources.append("src/petsc_linear_solver.cpp")

# Build library dir flags for linker
for lib_dir in petsc_library_dirs:
    extra_link_args.append("-L" + lib_dir)
for lib in petsc_libs:
    extra_link_args.append("-l" + lib)

extensions = [
    Extension(
        "tcad.core._bindings",
        sources=sources,
        include_dirs=["src", np.get_include()] + petsc_include_dirs,
        language="c++",
        define_macros=([("TCAD_CONSTANTS_LEGACY_CHARGE", "1")]
                       if selected_constants_profile == "legacy-charge" else []),
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
]

setup(
    cmdclass={"build": build, "build_ext": build_ext},
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
        annotate=False,
    ),
    zip_safe=False,
)
