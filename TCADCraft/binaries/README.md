# TCADCraft 0.3.0rc2 distribution

The current release candidate includes a native wheel built from a clean sdist,
with independently installed package checks outside the source tree.

## Install

Target: **Linux x86_64, CPython 3.13**, SI constants and GCC float128
(113 mantissa bits). This host-built wheel is not manylinux-certified.
Other Python ABIs, operating systems and architectures need source builds.
Runtime libquadmath/libstdc++ and compatible libc must be available; inspect
[compatibility](linux-x86_64/compatibility-0.3.0rc2.json).

```bash
cd EDACraft/TCADCraft
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install binaries/linux-x86_64/tcad-0.3.0rc2-cp313-cp313-linux_x86_64.whl
python -c "import tcad; print(tcad.__version__)"
(cd binaries && sha256sum -c SHA256SUMS)
```

Pip resolves Python dependencies; provision them separately for offline use.

## Artifacts and checks

- [Linux wheel](linux-x86_64/tcad-0.3.0rc2-cp313-cp313-linux_x86_64.whl)
- [Source distribution](source/tcad-0.3.0rc2.tar.gz)
- [SHA-256 checksums](SHA256SUMS)
- [Fresh build/install report](../docs/releases/0.3.0rc2/RELEASE_VERIFICATION.json)
- [JUnit results](../docs/releases/0.3.0rc2/targeted_tests.xml)
- [Validation scope](../docs/releases/0.3.0rc2/VALIDATION.md)
- [Packaging corrections and preserved failures](../docs/releases/0.3.0rc2/packaging_attempts.json)

Installed-package tests: **1127 passed, 0 skipped, zero failures/errors**,
including all sheet modules, ordering/cache/trace regressions and native
constants/precision contracts. README graphene and MoS2 examples both pass
with `GEOMETRIC_ND`. This is targeted validation, not the full development
suite or whole-device/commercial/experimental qualification.

The sdist includes all controlled numerical sources and compact report scripts
and fixtures. The wheel also includes auxiliary native kernel sources.
Final packaging reports, artifact links, checksums and handoff were added to
the repository after building; they do not change the validated numerical code.
Full raw validation archives are not bundled. Production was not replaced.

Previous 0.3.0rc1 artifacts and [compatibility](linux-x86_64/compatibility-0.3.0rc1.json)
are retained; the immutable `tcadcraft-v0.3.0rc1` tag remains available.
