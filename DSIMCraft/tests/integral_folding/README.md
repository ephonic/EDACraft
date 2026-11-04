# Integral folding and shared semantic bodies

The integral constant-function interpreter declines handles, null, real values and unpacked values before packed-width queries. Integral return types do not make runtime operands constant. Real constant evaluation is not implemented by this interpreter; the normal runtime lowering still handles those expressions.

Semantic subroutine bodies are cached by declaration and lexical scope for one parser lifetime. Each call still validates its actual list, and lowering retains separate automatic activations. Cache entries are removed before parser cleanup. Symbol scopes start with at most 31 buckets and grow with their own declarations; outward lookup uses each scope's bucket count.

Integral conditional expressions evaluate the selected branch for known conditions, and evaluate both branches once in source order and merge four-state bits for an unknown condition. This includes pure reads of possibly null object fields.

Six executable fixtures check singleton initialization, class/chandle comparisons, real operand boundaries, integral parameter evaluation, conditional side effects/sign extension/X merging, and a shared method call graph with different receivers. Four negative cases include invalid actual lists after a valid cached call. The C++ semantic-memory test checks shared hive identity, repeated parser resets, and 4096-symbol parent/child scope growth, shadowing, duplicate rejection and deletion.

Run `ctest --test-dir <build> -R rtl_integral_folding --output-on-failure`, or use `python3 tests/integral_folding/regression.py <dsim> <output> <CMakeCache.txt>`. The regression checks three backend requests and 108 ordered/settled VCD/DWF/async captures.
