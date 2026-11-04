`timescale 1ns/1ps
module top;
localparam FILL=4'hf inside {'1};
localparam PRECEDENCE=2 inside {2} == 1;
localparam YES=4'bx101 inside {4'b????};
localparam MISS=3 inside {[8:2]};
localparam UNKNOWN=4'bx101 ==? 4'b0101;
localparam MIX=8'shff inside {16'shffff,32'h0};
localparam logic[129:0] WIDE=130'h200000000000000000000000000000001;
localparam WILDMATCH=WIDE ==? 130'h2xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx1;
localparam N=(7 inside {[1:9]})?5:2;
logic[N-1:0] bits_value=0;
wire[3:0] lanes;
genvar g;
generate for(g=0;g<4;g=g+1)begin: lane
 if(g inside {0,[2:3]})begin: included
  assign lanes[g]=1'b1;
 end else begin: excluded
  assign lanes[g]=1'b0;
 end
end endgenerate
initial begin
 #1 if(FILL!==1||PRECEDENCE!==1||YES!==1||MISS!==0||UNKNOWN!==1'bx||MIX!==0||WILDMATCH!==1||N!==5||$bits(bits_value)!==5||lanes!==4'b1101)$fatal(1,"constant/generate membership");
 $display("TRACE elaboration complete");
end
endmodule
