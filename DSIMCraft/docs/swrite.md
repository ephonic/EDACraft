# Display-style string writes

`$swrite` now accepts a destination alone (empty output), unformatted scalar
values, multiple format segments and dynamic string formats. Unconsumed numeric
arguments use decimal output with type-dependent width and signedness; real
arguments use general real formatting. `$swriteh`, `$swriteb` and `$swriteo`
select hexadecimal, binary and octal defaults. Explicit format conversions still
override those defaults.

Operands are evaluated once before formatting. A string consumed by `%s` is
output as data, so its percent signs are not interpreted again. Packed string
literals consumed by numeric conversions retain their integral representation.
Destinations include strings, string queue elements and packed variables; packed
outputs keep their existing width/truncation behavior. These tasks remain
zero-time operations allowed in functions.

Class/chandle output and unformatted unpacked aggregate output are explicitly
unsupported. VCS formats class values as object contents, so printing a numeric
handle would be incorrect. The unchanged full UVM library still stops on this
class-output requirement at `uvm_pool.svh:249`; complete UVM and `run_test` remain
unfinished. See `validation/m219-swrite` for same-source VCS and native evidence.
