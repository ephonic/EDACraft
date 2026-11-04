package coverage_types;
 typedef bit[31:0] coverage_bits_t;
 typedef enum coverage_bits_t {NO_COVERAGE=0,REG_BITS=1,ADDR_MAP=2,FIELD_VALS=4,ALL_COVERAGE=-1} coverage_e;
 typedef coverage_e alias_e;
 class coverage_model;
  coverage_e enabled=ALL_COVERAGE;
  function coverage_e get();return enabled;endfunction
  function void set(input alias_e mask);enabled=mask;endfunction
 endclass
endpackage
module top;
 import coverage_types::*;
 coverage_model model;alias_e current;bit[63:0] extended;
 initial begin
  model=new();current=model.get();extended=current;
  if(current!==32'hffffffff||extended!==64'h00000000ffffffff||current.name()!="ALL_COVERAGE")
   $fatal(1,"unsigned package enum");
  model.set(current.prev());current=model.get();
  if(current!==FIELD_VALS||current.name()!="FIELD_VALS")$fatal(1,"package enum identity");
  #1;$display("TRACE coverage %h %s %h",current,current.name(),extended);$finish;
 end
endmodule
