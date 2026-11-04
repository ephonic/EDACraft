`timescale 1ns/1ps
module lane #(parameter N=1)(output integer passed=0,failed=0);
  localparam COUNT=N+1;
  reg clk=0;reg [3:0] value=4'b1111;integer tick=0;
  always #(N+3) clk=~clk;
  property p;
    @(posedge clk) value[N] |=> ##(N-1) value[N][*COUNT] ##0 (value[0]===value[N])[* (N+1)];
  endproperty
  check_p:assert property(p) passed++;else failed++;
  initial begin
    repeat(14)begin
      @(negedge clk);tick++;
      value=(tick%5==2)?4'bxxxx:((tick%4==1)?4'b0000:4'b1111);
    end
  end
endmodule
module top;
  wire [31:0] a,b,c,d,e,f;
  lane #(1) one(a,b);lane #(2) two(c,d);
  for(genvar g=1;g<2;g++)begin:lanes
    lane #(g) generated(e,f);
  end
  initial begin
    #151;
    $display("TRACE repeat-clones %0d %0d %0d %0d %0d %0d",a,b,c,d,e,f);
    if(a!==e||b!==f)$fatal(1,"repetition generate clone mismatch");
    $finish;
  end
endmodule
