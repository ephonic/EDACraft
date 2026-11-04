module top;
 typedef struct {int id;string name;} Entry;
 class Factory;
  Entry entries[$];
  function void add(input string name,input int id);
   Entry entry;entry.name=name;entry.id=id;entries.push_back(entry);
  endfunction
 endclass
 Factory factory;int observed;
 initial begin
  factory=new;factory.add("packet",7);
  if(factory.entries.size()!=1||factory.entries[0].id!=7||factory.entries[0].name!="packet")$fatal(1,"struct string queue");
  observed=factory.entries[0].id;
  $display("TRACE struct_string_queue %0d %s",factory.entries[0].id,factory.entries[0].name);$finish;
 end
endmodule
