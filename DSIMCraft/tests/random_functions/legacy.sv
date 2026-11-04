`timescale 1ns/1ps
module top;
 integer seed,r,i,j;
 logic[63:0] wide;
 initial begin
  for(j=0;j<13;j++)begin
   case(j)0:seed=0;1:seed=1;2:seed=-1;3:seed=123;4:seed=32'h80000000;5:seed=32'h7fffffff;6:seed=32'h5a1d58fb;7:seed=32'h7988bbf6;8:seed=32'h1f6b62fb;9:seed=32'h343ab1f6;10:seed=32'h777653fb;11:seed=32'hb43ab1f6;12:seed=32'hdc9d58fb;endcase
   for(i=0;i<8;i++)begin
    r=$random(seed);$display("TRACE legacy %0d %0d %0h %0h",j,i,r,seed);
   end
  end
  seed=1;wide=$random(seed);
  if(wide!==64'hffffffff80010e00)$fatal(1,"signed result");
  $display("TRACE legacy signed %0h",wide);
  #1;wide=$random;
  if(wide!==64'hffffffff9c598438)$fatal(1,"global stream");
  r=$random();if(r!==32'h43593986)$fatal(1,"global continuation");
  $display("TRACE legacy global pass");
 end
endmodule
