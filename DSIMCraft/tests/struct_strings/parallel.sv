module lane #(parameter int DELAY=1)(output int count,output bit error);
 typedef struct {string name;int number;} item_t;
 item_t a,b;
 initial begin
  count=0;error=0;
  for(int i=0;i<3;i++)begin
   #DELAY;a.name="lane";a.number=i;b=a;b.name="copy";
   if(a.name!="lane"||b.name!="copy"||b.number!=i)error=1;
   count++;
  end
 end
endmodule
module top;
 wire [31:0] ca,cb;wire ea,eb;
 lane #(.DELAY(1)) u(ca,ea);lane #(.DELAY(2)) v(cb,eb);
endmodule
