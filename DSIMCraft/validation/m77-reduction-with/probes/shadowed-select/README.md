# Default iterator selection and an external item

The original first values fixture declares `integer item=99`. Bare `item` within
with maps the actual element in VCS, but `item[3:0]` maps the external integer's
low nibble 3: sum over three elements gives 9. The `[15:8]` source's `item[11:8]`
also observes the external integer, giving 0 after int conversion.

An isolated probe without an external item preserves the source range:
[iterator-query.log](../iterator-query.log) reports left/right sums 30/16,
8-bit width sum16, low [3:0] selects0 and original [11:8] selects6.
The initial interpretation as normalized indices was therefore discarded.

Raw source, dump, compile/run logs and VCD remain unchanged here. dsim now binds
both primary and packed-select paths to the lexical iterator. The native-only
shadowed_select fixture checks sub=4 and selected=6. The shared values fixture
uses a named x iterator for selections and is compared against VCS without
excluding any physical bits. This original default-selection case is not counted
as a VCS alignment pass.
