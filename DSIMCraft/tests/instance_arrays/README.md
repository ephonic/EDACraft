# Instance array regression

Run `ctest --test-dir build -R '^rtl_instance_arrays$' --output-on-failure`.
Seven shared sources run on serial, wheel and two-worker backends, comparing
complete ordered and settled event streams in VCD and DWF. Three programs force
a failed prediction and compare replay output; `parallel` checks two actual
partitions and both independent final outputs. Eleven rejected models check
invalid ranges/widths and explicit unsupported boundaries.

`expected.json` contains TRACE expectations; source assertions independently
check arithmetic, state isolation, port mapping and four-state resolution.
`validation/m73-instance-arrays` contains real VCS source/log/wave evidence,
strict per-bit comparison, sanitizer checks and publication records.
