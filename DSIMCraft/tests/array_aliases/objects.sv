module top;
 class Base;
  int v;function new(int n=1);v=n;endfunction
  virtual function int get();return v;endfunction
 endclass
 class Child extends Base;
  function new(int n=1);super.new(n);endfunction
  virtual function int get();return v+10;endfunction
 endclass
 class Builder #(type TYPE=Base);
  typedef TYPE Queue[$];
  static function Queue pack(input TYPE value);
   Queue tmp;tmp.push_back(value);return tmp;
  endfunction
  static function int total(input Queue values);
   int n;n=0;foreach(values[i])n+=values[i].get();return n;
  endfunction
 endclass
 typedef Base Q[$];
 Q q;Base b;Child c;
 int observed;
 initial begin
  c=new(7);q=Builder#(Base)::pack(c);b=q[0];
  $display("TRACE objects %0d %0d %0d",q.size(),b.get(),Builder#(Base)::total(q));
  c.v=20;observed=q[0].get();$display("TRACE identity %0d",q[0].get());#1;$finish;
 end
endmodule
