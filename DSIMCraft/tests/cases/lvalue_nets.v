module top;
  reg [3:0] hi,lo;
  reg en,bit_in;
  wire [7:0] bus,split;
  wire dup;
  wire [63:0] edge_bus;
  assign bus[7:4]=hi;
  assign bus[3:0]=en?lo:4'bzzzz;
  assign bus[5:2]=4'b1010;
  assign {split[7:4],split[3:0]}={lo,hi};
  assign {dup,dup}=2'b10;
  buf high_bit(edge_bus[63],bit_in);
  assign edge_bus[62:0]=63'd1;
  initial begin
    hi=4'ha; lo=4'h5; en=1; bit_in=1;
    #1 $display("TRACE bus=%b split=%h dup=%b edge=%h",bus,split,dup,edge_bus);
    en=0;
    #1 $display("TRACE bus=%b split=%h",bus,split);
    hi=4'hf; bit_in=0;
    #1 $display("TRACE bus=%b split=%h edge=%h",bus,split,edge_bus);
    $finish;
  end
endmodule
