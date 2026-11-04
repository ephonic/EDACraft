// probe: unpacked struct + struct array
`timescale 1ns/1ps
module tb;
    typedef struct {
        logic [7:0] addr;
        logic [7:0] data;
    } pkt_t;
    pkt_t pkts [0:1];
    initial begin
        pkts[0].addr = 8'h11; pkts[0].data = 8'h22;
        pkts[1].addr = 8'h33; pkts[1].data = 8'h44;
        if (pkts[0].addr == 8'h11 && pkts[1].data == 8'h44)
            $display("PROBE_UNPACKED_STRUCT: ok");
        else
            $display("PROBE_UNPACKED_STRUCT: BAD");
        $finish;
    end
endmodule
