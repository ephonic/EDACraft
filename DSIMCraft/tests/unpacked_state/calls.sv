`timescale 1ns/1ps
module top;
  typedef struct {bit [7:0] bits;logic [7:0] raw;} item_t;
  item_t s,want;
  int bad_defaults=0;
  function automatic item_t make(input logic [7:0] value);
    item_t local_value;
    begin
      if(local_value.bits!==0||local_value.raw!==8'bx)bad_defaults++;
      local_value.bits[7:0]=value;local_value.raw=value;
      make=local_value;
    end
  endfunction
  task automatic modify(ref item_t value);
    item_t zero;
    begin
      zero.bits=0;zero.raw=0;
      value.bits+=8'bx;value.raw=0;
      if(value!==zero)$fatal(1,"ref struct state conversion");
    end
  endtask
  task automatic fill(output item_t value);
    begin {value.bits,value.raw}=16'bxz10_zx01_xz10_zx01;end
  endtask
  initial begin
    s=make(8'bxz10_zx01);want.bits=8'h21;want.raw=8'bxz10_zx01;
    if(s!==want)$fatal(1,"struct function return");
    modify(s);want.bits=0;want.raw=0;
    if(s!==want)$fatal(1,"ref copy persistence");
    fill(s);want.bits=8'h21;want.raw=8'bxz10_zx01;
    if(s!==want)$fatal(1,"output struct copyout");
    s=make(8'hz);want.bits=0;want.raw=8'hz;
    if(s!==want||bad_defaults!=0)$fatal(1,"automatic frame reuse/defaults");
    $display("TRACE calls %b %b",s.bits,s.raw);
    #1;$finish;
  end
endmodule
