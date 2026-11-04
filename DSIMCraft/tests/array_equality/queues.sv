class C;
 string values[$];
 function bit same(C rhs);return values===rhs.values;endfunction
endclass
module top;
 bit observed=0;
 string a[$],b[$]; C x,y;
 initial begin
  observed=1;
  $display("TRACE empty %b %b %b %b",a==b,a!=b,a===b,a!==b);
  a.push_back("first");b.push_back("first");
  $display("TRACE equal %b %b %b %b",a==b,a!=b,a===b,a!==b);
  b.push_back("second");
  $display("TRACE size %b %b %b %b",a==b,a!=b,a===b,a!==b);
  a.push_back("Second");
  $display("TRACE text %b %b",a===b,a!==b);
  x=new;y=new;x.values=a;y.values=a;
  $display("TRACE property %b",x.same(y));
  y.values.pop_back();$display("TRACE property-size %b",x.same(y));
 end
endmodule
