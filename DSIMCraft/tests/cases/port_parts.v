module endpoint(input en,input [3:0] d,inout [3:0] bus,output [3:0] seen);
  assign bus=en?d:4'bzzzz;
  assign seen=bus;
endmodule
module wrapper(input en,input [3:0] d,inout [3:0] bus,output [3:0] seen);
  endpoint inner(en,d,bus,seen);
endmodule
module state_cell(input [7:0] d,output reg [7:0] q);
  always @(d) q<=d;
endmodule
module readback(output [3:0] y,output [3:0] seen);
  assign y=4'bzzzz;
  assign seen=y;
endmodule
module injector(input [1:0] bus);
  assign bus=2'b10;
endmodule
module repeated(input [1:0] d,output [1:0] y,output [1:0] seen);
  assign y=d;
  assign seen=y;
endmodule
module narrow(output reg [3:0] q);
  initial q=4'ha;
endmodule
module top;
  reg en,ext_en;
  reg [3:0] d;
  reg [7:0] state_d;
  wire [15:8] bus;
  wire [11:8] seen;
  wire [11:0] state_out;
  wire [7:0] external;
  wire [3:0] external_seen,input_bus;
  wire repeat_net;
  wire [1:0] repeat_seen;
  wire [3:0] input_concat;
  wire [11:0] widened;
  wrapper wrap(.en(en),.d(d),.bus({bus[9:8],bus[15:14]}),.seen(seen));
  assign bus[15:14]=ext_en?2'b01:2'bzz;
  state_cell st(.d(state_d),.q({state_out[11:8],state_out[3:0]}));
  readback rb(.y(external[7:4]),.seen(external_seen));
  assign external[7:4]=4'hb;
  injector inject(.bus(input_bus[3:2]));
  injector inject_concat(.bus({input_concat[3],input_concat[0]}));
  repeated rep(.d(2'b10),.y({repeat_net,repeat_net}),.seen(repeat_seen));
  narrow nw(.q({widened[11:8],widened[3:0]}));
  initial begin
    en=0; ext_en=1; d=4'ha; state_d=8'hd6;
    #1 $display("TRACE bus=%b seen=%b state=%h read=%h input=%b repeat=%b/%b wide=%h concat_input=%b",bus,seen,state_out,external_seen,input_bus,repeat_net,repeat_seen,widened,input_concat);
    en=1;
    #1 $display("TRACE bus=%b seen=%b",bus,seen);
    ext_en=0;
    #1 $display("TRACE bus=%b seen=%b",bus,seen);
    en=0;
    #1 $display("TRACE bus=%b seen=%b",bus,seen);
    $finish;
  end
endmodule
