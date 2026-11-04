# Dynamic array arguments

M65 adds one-dimensional integral dynamic array actuals to automatic task/function
`input`, `output`, `inout`, `ref` and `const ref` unsized formals. The RTL parser
and gate parser remain separate.

```systemverilog
integer samples[], result[];
task automatic grow(input integer src[], output integer dst[]);
  #2;
  dst = new[src.size()+1](src);
  dst[src.size()] = 42;
endtask
initial begin
  samples = new[2]; samples[0] = 7; samples[1] = 8;
  grow(samples, result); // result now has three independent elements
end
```

Value inputs snapshot both size and contents at entry. Outputs start empty on
entry. Inout arguments snapshot at entry and copy back at normal return. Copyout
replaces the actual's size and contents; mutations of an input formal stay local.
The same call site may receive empty arrays or different lengths on every call.
Named/default arguments, classic task declarations, nested forwarding, runtime
array queries, `foreach`, two-state and wide integral elements use the existing
compiled call paths.

Ref arguments alias the actual descriptor: element writes, resize, replacement
and `delete()` are immediately visible through all aliases. Const ref observes
live changes, including across task suspension and event waits. Writes and
forwarding into writable ref/output/inout arguments are conservatively rejected.
The existing M62 compatibility difference remains: VCS accepts some const-ref
copyout paths that dsim rejects.

Value containers belong to `Sim`, not host closures. Activation frames isolate
concurrent calls, cancellation skips copyout, and reused slots start empty.
Descriptor dependencies constrain partition placement. Container state and alias
frames participate in checkpoints and failed-prediction restoration.

Current boundaries:

- Dynamic actuals require one complete unsized dimension. M70 permits
  [equal-width state conversion](array-state-conversion.md) for value formals;
  ref/const-ref require equivalent integral element types. Dynamic elements cannot
  yet bind scalar ref arguments. Fixed
  formals cannot receive dynamic actuals, even if lengths happen to match.
- Fixed actuals retain M63's call-site shape specialization for input/inout `[]`;
  those formal instances do not support runtime resizing or dynamic methods.
  Fixed actuals cannot bind output/ref/const-ref `[]`.
- Static unsized subroutines, recursive calls, multidimensional dynamic storage,
  array returns, assignment patterns and broader type
  conversions remain unsupported.
- Dynamic waveform element declarations remain unavailable. Validation checks
  every exported physical bit plus shared scalar observations and TRACE values;
  this is not a dump of every allocated dynamic element.
- No new performance benchmark is claimed by this functional change.

M66 adds [dynamic element NBA](dynamic-nba.md) with separate VCS compatibility
boundaries for ref formals.

Validation: [M65 evidence](../validation/m65-dynamic-arguments/README.md).
