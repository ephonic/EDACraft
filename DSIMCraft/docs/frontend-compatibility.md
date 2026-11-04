# Packed dimensions, generate steps and root selection

RTL module ports and variables support multiple packed dimensions, including
parameterized bounds, non-ANSI declarations, typedefs and task/function value
parameters. Dimensions retain their source shape for indexing and array queries;
storage and whole-port connections use a flat packed value in declaration order.
The separate gate-netlist parser is unchanged.

```systemverilog
module lanes #(parameter N=2, W=8)(
  input wire [N-1:0][W-1:0] a,
  output wire [N-1:0][W-1:0] y
);
  for (genvar i=0; i<N; i++) begin: lane
    assign y[i] = a[i] + i;
  end
endmodule
```

Constant indices lower directly to bit offsets. Runtime subscripts are evaluated
once and checked dimension by dimension before flattening, including wide and
unknown indices, so an invalid subscript cannot address an adjacent row. Reads
and writes reuse existing signal, memory, NBA, partition and checkpoint paths.
Both dimension directions and signed declaration bounds are supported. A final
ordinary or indexed part-select selects a constant number of elements; ordinary
part-select direction must agree with its declaration. Total packed storage and
selected result widths remain limited to 1,048,576 bits.

The multidimensional out-of-range policy matches the installed VCS W-2024.09:
an entirely or partially invalid selection reads all X and suppresses the entire
write. A two-state destination/read converts X to zero through existing storage
rules. The one-dimensional packed select implementation retains its previous
clipping behavior. The original partial-range difference and probe are retained
in [M72](../validation/m72-frontend-compat/README.md).

Generate loops accept `i++`, `++i`, `i--` and `--i`, in addition to assignment
steps. These update forms normalize to the existing genvar assignment elaborator;
they do not add runtime processes. The existing convergence and iteration limits
remain in force.

Without `--top`, dsim selects the unique module that is not instantiated by
another module, independent of declaration order or its name. For compatibility
with earlier dsim invocations, a root named `top` is preferred when several roots
exist. Otherwise the diagnostic lists the candidates and requires `--top NAME`.
Unlike VCS, this does not execute several independent root modules in one model.
An explicit `--top`/`-top` continues to select one module.

```sh
dsim design.sv testbench.sv -o simv
dsim --top matvec_tb design.sv testbench.sv -o simv
dsim --language verilog legacy.v -o simv
```

The default RTL keyword set remains SystemVerilog, including for `.v` files, to
preserve existing invocations. `--language verilog` (alias `--verilog`) releases
SystemVerilog-only keywords such as `ref`, `logic`, `const` and `new` for ordinary
Verilog identifiers. `--language systemverilog`, `-sverilog` and `--systemverilog`
select the default keyword set. In SystemVerilog, `ref` remains reserved; use an
escaped identifier `\ref `, terminated by whitespace, when that spelling is
required. This keyword switch is not a claim of complete language-version
conformance or automatic per-file language selection.

General variable output/inout port slices, part-selects followed by another
subscript, arbitrary indexed expression results and complete SystemVerilog array
type compatibility remain outside this change. Packed aggregate member selects
retain their previous support boundary. Validation uses
`ctest --test-dir build -R '^(rtl_frontend_compat|rtl_semantic_memory)$' --output-on-failure`.
