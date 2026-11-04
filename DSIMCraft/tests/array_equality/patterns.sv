module top;
 bit observed=0;
 typedef struct {string name;string path;} Field;
 Field entries[$],other[$];
 function automatic string render(Field value);
  return {value.name,":",value.path};
 endfunction
 initial begin
  observed=1;
  entries.push_back('{"item","item[+]"});
  other.push_back('{name:"item",path:"item[+]"});
  $display("TRACE pattern %s",render(entries[0]));
  $display("TRACE field %s %s %b",entries[0].name,entries[0].path,entries===other);
  other[0].path="different";
  $display("TRACE struct-text %b %b",entries==other,entries!==other);
 end
endmodule
