# Profile-guided compilation of generated models

PGO optimizes each generated simulation executable. Rebuilding only the dsim frontend with PGO does not optimize the loops inside its output. The existing `--cxx-flag` option passes literal compiler arguments; it can supply GCC's profile generation/use options without changing default compiler settings.

For a deterministic, plain RTL model, use a fresh working/profile directory and the same generated C++, compiler flags and output executable path in both compilation phases:

```sh
mkdir /tmp/dsim-pgo-example
cd /tmp/dsim-pgo-example
/path/to/dsim design.sv tb.sv --top tb --emit-only --emit-cpp model.cpp
g++ -std=c++17 -O2 -pthread -fprofile-generate=/tmp/dsim-pgo-example/profiles model.cpp -o simv
./simv --max-events 100000000000
g++ -std=c++17 -O2 -pthread -fprofile-use=/tmp/dsim-pgo-example/profiles -Werror=missing-profile -Werror=coverage-mismatch model.cpp -o simv
./simv --max-events 100000000000
```

The repository also provides an automated workflow. It freezes the input C++, requires a new work directory, retains commands/logs/profile hashes in `pgo.json`, and makes missing/mismatched profile data fatal:

```sh
python3 /path/to/dsim/scripts/build_pgo.py model.cpp --cxx g++ \
  --work /tmp/dsim-trained-model --run-dir /path/to/training-inputs \
  --train-arg=--max-events --train-arg=100000000000 --verify
```

The result is `/tmp/dsim-trained-model/simv`. `--verify` runs the optimized executable with the same arguments and compares complete stdout; use it for deterministic, repeatable training inputs. `--cxx-flag` adds a literal compiler argument, for example an include/library option. The script supports GCC profile data; it rejects Apple Clang before creating a work directory. Relative file inputs resolve under `--run-dir` in both training and verification. An existing work directory is left untouched.

Alternatively, compile both phases through dsim with `--cxx g++ --cxx-flag=-fprofile-generate=/absolute/profile/directory` and then `--cxx-flag=-fprofile-use=/absolute/profile/directory`. Use the same `--emit-cpp` and `-o` paths and the same source/options in both commands; add both `--cxx-flag=-Werror=missing-profile` and `--cxx-flag=-Werror=coverage-mismatch` in the use phase. Profile data belongs to the generated model and toolchain. Regenerate it after changing the model or compiler options. Wave-enabled standalone C++ builds also need the Zstandard include/library options normally supplied by the dsim driver.

Training executes the simulation and adds an instrumented build plus an optimized rebuild. Choose representative inputs and include that extra cost when evaluating short jobs. PGO remains optional; no default `-O3`, architecture flags or floating-point relaxations are implied.

[M113](../validation/m113-generated-regions/README.md) measures this separately on frozen M111 C++ with GCC 11.5, CPU 0 and the unchanged complete perf-kit workloads. Each model trains once on the same complete workload used for evaluation; those results establish this workload's benefit, not generalization to other inputs. Baseline/PGO/VCS run after all compilations, with one warmup and three rotated rounds. Complete outputs are checked, and profile mismatches are compilation errors. These results do not describe a PGO build of the subsequent loop-budget candidate.
