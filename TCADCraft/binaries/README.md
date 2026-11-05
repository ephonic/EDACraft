# TCADCraft 0.3.0rc1 distribution

This release candidate contains an installable native wheel and its source
distribution. These files were built from the same clean source distribution;
the wheel was installed and checked outside the source tree.

## Install the Linux wheel

Target: **Linux x86_64, CPython 3.13**, SI constants and native GCC float128
(113 mantissa bits). This is a host-built Linux wheel, not a certified manylinux
wheel. Other Python versions, architectures and operating systems need a source
build. Runtime shared libraries, including libquadmath, must be available.
See [compatibility.json](linux-x86_64/compatibility.json) for actual libc and
shared-library dependencies from the tested host.

```bash
cd EDACraft/TCADCraft
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install binaries/linux-x86_64/tcad-0.3.0rc1-cp313-cp313-linux_x86_64.whl
python -c "import tcad; print(tcad.__version__)"
```

Pip resolves the declared Python dependencies. Use an environment with access
to a package index, or provision those dependencies separately for offline use.

## Artifacts and verification

- [Linux wheel](linux-x86_64/tcad-0.3.0rc1-cp313-cp313-linux_x86_64.whl)
- [Source distribution](source/tcad-0.3.0rc1.tar.gz)
- [SHA-256 checksums](SHA256SUMS)
- [Build/install report](../docs/releases/0.3.0rc1/RELEASE_VERIFICATION.json)
- [JUnit results](../docs/releases/0.3.0rc1/targeted_tests.xml)

```bash
cd binaries
sha256sum -c SHA256SUMS
```

Installed-package checks: **1055 passed, 0 skipped; zero failures/errors**. Both the README graphene example and
the MoS2 contact variant passed. This is targeted validation, not a rerun of the
entire development suite or complete physical/device acceptance.

The source archive includes the build helper, C++/Cython sources, tests,
fixtures and compact technical documentation. Repository-only binary download
links, checksums and final packaging reports were added after that build;
they do not change the packaged numerical code. No production installation
was replaced by this GitHub publication.
