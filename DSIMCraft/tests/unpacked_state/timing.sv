`timescale 1ns/1ps
module top;
  typedef struct {bit [7:0] bits;logic [7:0] raw;} item_t;
  item_t s,want,rows[0:1];
  event tick;
  int index=0, calls=0;
  function automatic logic [7:0] source();
    begin calls++;source=8'bxz10_zx01;end
  endfunction
  initial begin
    s.bits=0;s.raw=0;want=s;rows[0]=s;rows[1]=s;
    s.bits<=#2 source();s.raw<=#2 8'bxz10_zx01;
    #1;if(s!==want)$fatal(1,"delayed NBA committed early");
    #2;want.bits=8'h21;want.raw=8'bxz10_zx01;
    if(s!==want||calls!=1)$fatal(1,"delayed NBA member state");
    {rows[index++].bits,s.bits[3:0]}<=@(tick)12'bxz01_zx10_zzx1;
    if(index!=1)$fatal(1,"event NBA address capture");
    index=1;#1;->tick;#1;
    want.bits=8'h21;
    if(s!==want||rows[0].bits!==8'h12||rows[1].bits!==0)$fatal(1,"event NBA concat conversion");
    s.bits=#2 8'bxz01_zx10;want.bits=8'h12;
    if(s!==want)$fatal(1,"blocking intra-assignment delay");
    $display("TRACE timing %b %b %b %0d %0d",s.bits,s.raw,rows[0].bits,index,calls);
    #1;$finish;
  end
endmodule
