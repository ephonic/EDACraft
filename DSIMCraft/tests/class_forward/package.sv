`timescale 1ps/1ps
package objects;
 typedef class Payload;
 typedef Payload Alias;
 class Holder;
  Alias value;
  function Payload get();return value;endfunction
 endclass
 class Payload;
  Holder parent;
  string text="payload";
  logic [128:0] bits=129'h1f123456789abcdef0;
 endclass
 function automatic Alias identity(Payload value);return value;endfunction
endpackage
package exposed;
 import objects::Holder,objects::Alias,objects::Payload,objects::identity;
 export objects::*;
endpackage
module top;
 import exposed::*;
 Holder h;Alias p,q;logic [128:0] observed;
 initial begin
  h=new;p=new;h.value=p;p.parent=h;q=identity(h.get());observed=q.bits;
  #1;$display("TRACE package %s %h %0d",q.text,observed,q.parent==h);
 end
endmodule
