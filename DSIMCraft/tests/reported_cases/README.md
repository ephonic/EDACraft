# User-reported cases

These fixtures come from ~/vibe-coding/dsim-test/cases. Original archives and
logs there are retained unchanged. Every batch first checks that directory for
new unresolved reports and follows existing followup/rejection annotations.

carry_baseline uses the exact original RTL and unrolled TB. A previous binary
hit the explicit 180-second compile budget. Later archived runs and the M71
recheck pass all 290 observations against real VCS and independent expected bits.
A current compile-time budget failure remains a regression failure; it must not
be relabeled as a numerical mismatch.

The other five variants preserve original RTL, vector bytes, output inventory
and independent expected values. Their original TB drove data and active clock
controls in one SV region and is archived as harness-rejected. Here data inputs
drive first, #1 settles them, then clocks/resets drive, and #3 precedes observation.
The total four-unit event period is preserved. These are explicitly corrected
harness configurations, not claims that the original race has a unique result.
All 7,919 corrected observations match actual VCS W-2024.09 and independent bits.
origin.json records each source and transformation; regression.py checks RTL,
original unmodified TB where applicable, and stimulus fingerprints.

The local stable publisher runs all six models before replacing bin/dsim.
Run `ctest --test-dir build -R '^rtl_reported_cases$' --output-on-failure`.
