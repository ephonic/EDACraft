module top;
 class Phase;
  string name;
  function new(string n);name=n;endfunction
  function string get_full_name();return name;endfunction
 endclass
 Phase phases[$],p; int observed;
 initial begin
  p=new("z");phases.push_back(p);
  p=new("a");phases.push_back(p);
  p=new("m");phases.push_back(p);
  phases.sort with (item.get_full_name());
  if(phases[0].name!="a"||phases[1].name!="m"||phases[2].name!="z")$fatal(1,"sort keys");
  observed=phases.size();
  $display("TRACE phase_sort %s %s %s",phases[0].name,phases[1].name,phases[2].name);
  $finish;
 end
endmodule
