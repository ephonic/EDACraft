module top;
  bit bits[];
  logic[7:0] value=8'h96;
  int observed;
  initial begin
    {<<bit{bits}}=value;
    bits=new[$bits(value)](bits);
    observed=bits.size();
    $display("TRACE stream target %0d %b%b%b%b%b%b%b%b",observed,
             bits[0],bits[1],bits[2],bits[3],bits[4],bits[5],bits[6],bits[7]);
  end
endmodule
