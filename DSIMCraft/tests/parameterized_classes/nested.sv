module top;
 class Item;int v;function new(int n);v=n;endfunction endclass
 class Holder#(type T=int,type U=T,parameter int N=3);
 T value;U other;logic[N-1:0] lane;
 function new(T a,U b);value=a;other=b;lane='1;endfunction
 function T get();return value;endfunction
 endclass
 class Link#(type T=int);T value;Link#(T) next;
 function new(T v);value=v;endfunction
 function Link#(T) me();return this;endfunction
 endclass
 typedef Holder#(Item) H;
 typedef Holder#(logic[95:0],logic[95:0],9) Wide;
 typedef Holder#(Wide) Outer;
 typedef Link#(logic[64:0]) L;
 Item i;H h;Wide w;Outer o;L a,b;logic[95:0] observed;logic[64:0] link_value;int item_value;
 initial begin
 i=new(23);h=new(i,i);w=new(96'hffffffff1111222233334444,0);o=new(w,w);a=new(65'h1ffffffffffffffff);b=a.me();b.next=a;
 observed=o.get().get();link_value=b.next.value;item_value=h.get().v;
 $display("TRACE nested %0d %h %h",h.get().v,o.get().get(),b.next.value);
 end
endmodule
