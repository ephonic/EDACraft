`timescale 1ns/1ps
module top;
  string first="first",second="second",shared="seed";
  int done=0,checksum=0;
  task automatic convert(ref string target,input int value,input int delay_ns);
    string local_text;
    local_text.hextoa(value);
    #delay_ns;
    local_text.putc(0,8'h51);
    target=local_text;
    #1;target.putc(1,8'h41);
  endtask
  task automatic delayed_write(ref string target);
    #2;target.putc(1,8'h58);
    #2;target.itoa(-17);
  endtask
  initial begin convert(first,16'h1234,1);done++;end
  initial begin convert(second,16'h5678,2);done++;end
  initial delayed_write(shared);
  initial begin
    #1;shared="abcd";
    #1.5;
    if(first!="QA34"||second!="Q678"||shared!="aXcd")$fatal(1,"automatic/ref overlap");
    #1.5;
    if(first!="QA34"||second!="QA78"||shared!="-17"||done!=2)$fatal(1,"delayed mutation");
    checksum=shared.atoi();
    $display("TRACE lifetime %s %s %s %0d %0d",first,second,shared,done,checksum);
    $finish;
  end
endmodule
