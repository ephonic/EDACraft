package model;
 typedef class RegMap;
 typedef class Register;
 class MapInfo;int offset;function new(int value);offset=value;endfunction endclass
 class RegMap;
  local int submaps[RegMap];
  local string submap_rights[RegMap];
  local MapInfo regs_info[Register];
  function void add_submap(RegMap child,int base,string rights);submaps[child]=base;submap_rights[child]=rights;endfunction
  function void add_reg(Register reg_h,int offset);MapInfo info;info=new(offset);regs_info[reg_h]=info;endfunction
  function string get_rights(RegMap child);return submap_rights[child];endfunction
  function int address(Register reg_h);return regs_info[reg_h].offset;endfunction
 endclass
 class Register;int value=0;endclass
endpackage
module top;
 import model::*;
 RegMap root,a,b;Register r;int observed;
 initial begin
  root=new;a=new;b=new;r=new;
  root.add_submap(a,16,"RW");root.add_submap(b,32,"RO");root.add_reg(r,12);
  observed=root.address(r);
  if(root.get_rights(a)!="RW"||root.get_rights(b)!="RO"||root.get_rights(null)!=""||observed!=12)$fatal(1,"reg map associations");
  $display("TRACE UVM map %s %s %0d",root.get_rights(a),root.get_rights(b),observed);$finish;
 end
endmodule
