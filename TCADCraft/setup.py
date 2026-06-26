import os
import sys
import subprocess
import numpy as np
from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext
from Cython.Build import cythonize

class build_ext(_build_ext):
    """Custom build_ext that removes duplicate rpaths on macOS."""
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
is_arm64 = os.uname().machine in ("arm64", "aarch64")

extra_link_args = []
extra_compile_args = ["-std=c++17", "-O3"]

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
    if not petsc_available:
        extra_link_args.append("-framework")
        extra_link_args.append("Accelerate")
    
    # GCC on macOS needs explicit system library path for linking
    if petsc_available:
        extra_link_args.append("-L/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib")
    
    if not is_arm64:
        extra_link_args.append("-lquadmath")
else:
    # Linux / other
    extra_compile_args.append("-march=native")
    extra_link_args.append("-lquadmath")
    extra_link_args.append("-llapack")
    extra_link_args.append("-lblas")

if os.environ.get("TCAD_DEBUG"):
    extra_compile_args = ["-std=c++17", "-O0", "-g", "-fno-omit-frame-pointer"]
    if is_macos:
        extra_compile_args.append("-arch")
        extra_compile_args.append(os.uname().machine)

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
        extra_compile_args=extra_compile_args,
        extra_link_args=extra_link_args,
    )
]

setup(
    cmdclass={"build_ext": build_ext},
    ext_modules=cythonize(
        extensions,
        compiler_directives={"language_level": "3"},
        annotate=False,
    ),
    zip_safe=False,
)
