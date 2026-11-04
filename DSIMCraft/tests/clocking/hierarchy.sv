interface bus(input logic clk);
  logic [64:0] data=0;
  clocking cb @(posedge clk);
    input #1step sampled=data;
    output #0 driven=data;
  endclocking
endinterface
module top;
  bit clk=0;
  bus first(clk),second(clk);
  always #1 clk=~clk;
  initial begin
    @(first.cb);
    first.cb.driven<=65'h1_12345678_9abcdef0;
    second.cb.driven<=65'h0_fedcba98_76543210;
    @(second.cb);
    if(first.cb.sampled!==65'h1_12345678_9abcdef0 || second.cb.sampled!==65'h0_fedcba98_76543210)
      $fatal(1,"clocking instance isolation and wide values");
    $display("TRACE clocking hierarchy pass");
    $finish;
  end
endmodule
