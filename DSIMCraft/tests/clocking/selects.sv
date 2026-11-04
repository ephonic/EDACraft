module endpoint #(parameter W=65);
  bit clk=0;
  logic [W-1:0] data='h1ba;
  logic [0:7] ascending=8'hc3;
  int index=4;
  always #5 clk=~clk;
  clocking cb @(posedge clk);
    input sampled=data, copied=data;
    input asc=ascending;
  endclocking
  initial begin
    @(cb);
    if(cb.sampled[7:0]!==8'hba || cb.copied[8]!==1) $fatal(1,"aliased packed sample");
    if(cb.sampled[index+:4]!==4'hb) $fatal(1,"dynamic sampled select");
    if(cb.asc[0:3]!==4'hc || cb.asc[index+:4]!==4'h3) $fatal(1,"ascending sampled select");
    $display("TRACE clocking selects %0d",W);
  end
endmodule
module top;
  endpoint #(65) a();
  endpoint #(129) b();
  initial begin #6;$finish;end
endmodule
