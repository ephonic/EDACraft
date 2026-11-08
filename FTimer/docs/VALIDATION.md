# Validation scope: 0.1.1

The development standalone release dated 2026-11-08 passed **77/77 CTest entries**
in a Linux x86_64 Release build using GCC 11.5 and TBB disabled. These cover the
shared model, library handling, timing and parasitic mechanisms, power and SI
solver controls. Assertions were enabled for assertion-based regression programs.
The installed CMake SDK compiled and ran a consumer both before and after moving
the installation prefix. The CLI version and Python API were checked after the
version-banner update.

The same development timer implementation was rebuilt into fsyn, and three
timer power-interface regressions passed. Two broader fsyn integration tests
remained failing at SPEF connection-name and arithmetic-proof-binding checks;
this is not a claim that the complete synthesis regression suite passed.

The compact public snapshot retains the calculation sources and public headers,
with CLI/tools moved under `src`. It omits the development regression archive
and its process-specific reference inputs. Its source/CLI build, synthetic
timing and Python power examples, installation and SDK consumer are checked as
the publication validation. The full 77-entry development suite is a separate
validation result, rather than a test suite shipped in this directory.

## SI/CCSN limits

A single-cell linear holding-source plus distributed coupled-RC control was
checked against HSPICE and a continuous analytical solution. Across its three
controls and near/far observations, the maximum ftimer/HSPICE peak difference
was **0.005219%** and the maximum equivalent-width difference was **0.000305 ps**.
The width definition was twice the complete positive active-minus-quiet waveform
area divided by its peak.

PrimeTime's particular D-analysis branch differed from HSPICE by **4.83231%**
in the baseline control. Changing an independently driven aggressor stub caused
a PrimeTime peak change while the analytical/HSPICE victim response remained
unchanged. This investigation was closed with the HSPICE/analytical validated
RC solver retained; the private PrimeTime approximation was not uniquely proven.

This linear-model agreement does not establish complete nonlinear CCSN,
transistor-level, every-cell/PVT or full-design SI qualification. In particular,
the full-design arrival/WNS and general automatic CCSN reconstruction scope
remains unqualified. The target tolerances used during development must not be
read as universal achieved accuracy for arbitrary designs.

Private process libraries, native-tool licenses and the original comparison
archives are not part of the public source snapshot. The included Liberty files
are synthetic usage examples.
