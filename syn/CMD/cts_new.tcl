set CTSBUF	" \
	CLKBUFV10_12TL40 \
	CLKBUFV12_12TL40 \
	CLKBUFV16_12TL40 \
	CLKBUFV20_12TL40 \
	CLKBUFV8_12TL40 "

set CTSINV 	" \
	CLKINV10_12TL40 \
	CLKINV12_12TL40 \
	CLKINV16_12TL40 \
	CLKINV20_12TL40 \
	CLKINV8_12TL40 "
set CTSBUF_B "CLKBUFV20_12TL40"
set_clock_tree_references -references "$CTSINV"
set_clock_tree_references -references "$CTSINV"  -sizing_only
set_clock_tree_references -references "$CTSINV"  -delay_insertion_only
set_clock_tree_references -references "$CTSBUF_B" -boundary_cell_only
