module top;
 class C;
  static logic [128:0] wide=129'h100000000000000000000000000000001;
  static bit [128:0] clean;
  static string text="initial";
  static int aa[string];
  static int q[$];
  static int dyn[];
  static int fixed[0:1]='{4,9};
  static function void change();aa["a"]+=1;q.push_back(7);dyn=new[2];dyn[1]=13;endfunction
 endclass
 C c;int observed,n;logic [128:0] bits;
 initial begin
  C::change();c.aa["a"]+=2;c.q.push_back(3);c.dyn[0]=5;
  c.wide[127:64]=64'hxxzz1234;c.clean=c.wide;bits=C::wide;
  c.text="changed";C::text.putc(0,88);
  C::fixed[1]=21;
  observed=C::aa["a"]+c.dyn[0]+C::dyn[1]+c.fixed[1];n=C::q.pop_front();
  $display("TRACE storage %0d %0d %0d %s %h %h",observed,n,c.q.size(),C::text,C::wide,c.clean);
  #1;$finish;
 end
endmodule
