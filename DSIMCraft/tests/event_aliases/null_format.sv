class Box;event pulse;int value=3;endclass
module top;
 Box box;string text;int stage=0;
 initial begin
  box=new();box.pulse=null;$swrite(text,"%p",box);
  stage++;#1;$display("TRACE format %s",text);$finish;
 end
endmodule
