module top;
 bit [1:0] v;
 covergroup def;cp:coverpoint v{bins z={0};bins o={1};}endgroup
 covergroup threshold;option.per_instance=1;type_option.merge_instances=0;cp:coverpoint v{option.at_least=2;bins z={0};bins o={1};}endgroup
 covergroup cg_goal;option.per_instance=1;option.goal=50;cp:coverpoint v{bins each[]={0,1,2,3};}endgroup
 covergroup cp_goal;option.per_instance=1;cp:coverpoint v{option.goal=50;bins each[]={0,1,2,3};}endgroup
 def a,b;threshold c,d;cg_goal e;cp_goal f;
 initial begin
  a=new();b=new();v=0;a.sample();
  $display("TRACE default first %0f %0f %0f",a.get_coverage(),a.get_inst_coverage(),b.get_inst_coverage());
  v=1;b.sample();$display("TRACE default both %0f %0f %0f",a.get_coverage(),a.get_inst_coverage(),b.get_inst_coverage());
  c=new();d=new();v=0;c.sample();d.sample();
  $display("TRACE threshold %0f %0f %0f",c.get_coverage(),c.get_inst_coverage(),d.get_inst_coverage());
  e=new();f=new();v=0;e.sample();f.sample();
  $display("TRACE goals %0f %0f",e.get_inst_coverage(),f.get_inst_coverage());
  $finish;
 end
endmodule
