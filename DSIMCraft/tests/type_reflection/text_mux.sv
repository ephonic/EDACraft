module top;
 int calls;logic select;string result;
 class Obj;
 int id;
 function new(int n);id=n;endfunction
 function string name();calls++;return $sformatf("obj%0d",id);endfunction
 endclass
 Obj obj;
 function automatic string left();calls=calls*10+1;return "same";endfunction
 function automatic string right();calls=calls*10+2;return "same";endfunction
 function automatic string different();calls=calls*10+3;return "other";endfunction
 function automatic logic condition(logic v);calls=calls*10+4;return v;endfunction
 initial begin
 calls=0;result=condition(1)?left():right();$display("TRACE true [%s] %0d",result,calls);
 calls=0;result=condition(0)?left():right();$display("TRACE false [%s] %0d",result,calls);
 calls=0;result=condition(1'bx)?left():right();$display("TRACE unknown_same [%s] %0d",result,calls);
 calls=0;result=condition(1'bx)?left():different();$display("TRACE unknown_other [%s] %0d",result,calls);
 calls=0;result=obj==null?"null":obj.name();$display("TRACE null [%s] %0d",result,calls);
 obj=new(7);calls=0;result=obj==null?"null":obj.name();$display("TRACE object [%s] %0d",result,calls);
 end
endmodule
