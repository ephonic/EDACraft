module top;
 class Root;int value;function new(int x);value=x;endfunction endclass
 class Pool #(type KEY=int, T=Root, U=T);
  KEY key;T object;U alias_value;
  function new(KEY k,T v);key=k;object=v;alias_value=v;endfunction
  function int get();return object.value+alias_value.value;endfunction
 endclass
 Pool default_pool;
 Pool#(byte,Root) narrow;
 Pool#(.KEY(logic[64:0]),.U(Root)) wide;
 logic[64:0] observed;int total;
 initial begin
  Root r;r=new(9);default_pool=new(123,r);narrow=new(-2,r);wide=new('1,r);
  observed=wide.key;total=default_pool.get()+narrow.get()+wide.get();
  $display("TRACE types %0d %0d %h %0d",default_pool.key,narrow.key,observed,total);
 end
endmodule
