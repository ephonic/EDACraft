module top;
class PayloadQueue #(type T=int);
 T values[$];
 function void push(T value);values.push_back(value);endfunction
 function T pop();return values.pop_front();endfunction
 function int count();return values.size();endfunction
endclass
class Object;int id;endclass
class Registry;
 bit types[Object];
 function void add(Object key);types[key]=1;endfunction
 function bit contains(Object key);return types.exists(key);endfunction
endclass
PayloadQueue#(string) names;PayloadQueue#(int) ints;
Object a,b;Registry registry;string text;int observed;
initial begin
 names=new;ints=new;registry=new;a=new;b=new;
 names.push("uvm");names.push("packet");ints.push(17);registry.add(a);
 text=names.pop();if(text!="uvm" || names.values[0]!="packet" || names.count()!=1 || ints.pop()!=17)$fatal(1,"parameterized payload");
 if(!registry.contains(a)||registry.contains(b))$fatal(1,"object associative keys");
 observed=names.count()+registry.types.num();$display("TRACE UVM payloads %0d %s",observed,names.pop());
end
endmodule
