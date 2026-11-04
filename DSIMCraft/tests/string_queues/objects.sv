module top;
 class Args;
  string values[$];
  function void add(string s);values.push_back(s);endfunction
  function string take();return values.pop_front();endfunction
 endclass
 Args a,b;string q[$],s;int observed;
 initial begin
  a=new();b=new();a.add("alpha");a.values.push_front("beta");a.values.insert(1,"middle");
  b.values=a.values;q=b.values;a.values[1]="changed";
  if(b.values[1]!="middle"||q[1]!="middle"||a.values[1]!="changed")$fatal(1,"independence");
  s=a.take();if(s!="beta"||a.values[0].toupper()!="CHANGED")$fatal(1,"element methods");
  a.values.delete();if(a.values[0]!=""||a.take()!="")$fatal(1,"object defaults");
  observed=b.values.size()+q.size();$display("TRACE objects %s %0d",q[2],observed);$finish;
 end
endmodule
