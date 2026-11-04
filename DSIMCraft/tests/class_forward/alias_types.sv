module top;
 typedef class Pool;
 typedef Pool Alias;
 class Client;
  Pool p=new(29);
  function Pool pass(Pool x);return x;endfunction
  task change(ref Pool x, input Alias value);x=value;endtask
 endclass
 class Store #(type T=int);
  T value;
  function new(T x=23);value=x;endfunction
 endclass
 int by_handle[Alias];Alias handles[$];
 typedef Store#(int) Pool;
 Client c; Pool p; Alias a; Store#(int) direct; int observed;
 initial begin
  c=new;if(c.p.value!=29)$fatal(1,"forward alias property initializer");p=new(17);c.p=p;c.change(a,c.pass(p));direct=a;
  handles.push_back(direct);by_handle[p]=handles[0].value;
  foreach(by_handle[k])if(k!=p)$fatal(1,"alias key identity");
  observed=by_handle[direct];
  $display("TRACE alias %0d %0d %0d",observed,c.p==a,$cast(p,direct));
 end
endmodule
