module top;
 class Monitor;
  bit [1:0] value;
  covergroup cg;
   option.per_instance=1;
   cp: coverpoint this.value { bins zero={0};bins one={1}; }
  endgroup
  function new();cg=new();endfunction
  function void record(int v);value=v;cg.sample();endfunction
 endclass
 Monitor a,b;int observed;
 initial begin
  a=new();b=new();a.record(0);b.record(1);
  if(a.cg.get_inst_coverage()!=50.0||b.cg.get_inst_coverage()!=50.0)$fatal(1,"instance state");
  if(a.cg.get_coverage()!=100.0)$fatal(1,"type union");
  a.record(1);
  if(a.cg.get_inst_coverage()!=100.0||b.cg.get_inst_coverage()!=50.0||a.cg.get_coverage()!=100.0)$fatal(1,"receiver isolation");
  observed=int'(a.cg.get_coverage());$display("TRACE objects %0d",observed);$finish;
 end
endmodule
