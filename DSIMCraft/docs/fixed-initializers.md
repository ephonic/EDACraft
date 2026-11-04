# Fixed array declaration initialization

Fixed unpacked variable arrays can initialize by copying another compatible
fixed array or subarray. Each dimension must match in size; bounds and directions
can differ. Scalar packed integral elements may convert between two/four-state
storage at equal width. Signedness, atomic kind and enum identity are checked.
The existing equal-width, equal-signedness packed struct/union to integral array
copy conversion remains available. Ref and value array arguments retain their
separate compatibility rules. Multidimensional copies follow declaration order.

```systemverilog
logic [7:0] source[3:2];
task automatic sample(const ref logic [7:0] words[2]);
  bit [7:0] saved[2] = words, independent[1:0] = saved;
  // X/Z become zero in saved. independent retains its own values.
  #1;
endtask
```

Static initialization runs once before processes start. Explicit static locals
are shared across specialized calls. Automatic task/function/block locals copy
after argument copy-in on each scope entry, in declaration order. A runtime
subarray index is evaluated once, including its function side effects. Invalid
source subarrays use the existing X/zero default policy; that policy is not
claimed as complete VCS alignment.

Declaration copies use the existing array transfer path. Since an initializer
cannot suspend, its snapshot buffer stays in a local C++ block; it does not add
persistent host state to the scheduler or checkpoints. Initialization sources,
function effects and destination words remain in the owning partition. Automatic
frames, cancellation and failed predictions use the existing runtime.

The RTL grammar distinguishes declaration initializers before checking lvalue
prefixes, allowing two-bound ranges in every declaration dimension. Ordinary
assignment prefix slicing is still rejected. The shipped parser is regenerated
with Bison 3.8.2 and the verilog symbol prefix. The gate parser is unchanged.

Remaining limits include assignment patterns, fixed array initialization from
dynamic sources, array returns, net/port array initializers and general element
type/width conversion. A fixed array cannot use new[]. Ordinary scalar static
initialization keeps its earlier constant-only restriction. Previously recorded
VCS scheduling, bounds and dynamic constructor differences remain.

Validation: [M71](../validation/m71-reported-cases-fixed-initializers/README.md).
Run `ctest --test-dir build -R '^(rtl_fixed_initializers|rtl_semantic_memory)$' --output-on-failure`.
