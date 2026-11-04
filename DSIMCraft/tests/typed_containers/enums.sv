module top;
 typedef enum logic[2:0] {RED=1,GREEN=3,BLUE=5} Color;
 Color q[$],a[int],d[],last;
 int observed;
 initial begin
 q.push_back(RED);q.push_front(BLUE);q.insert(1,GREEN);
 last=q.pop_back();a[-2]=last;d=new[2];d[0]=q[0];d[1]=a[-2];
 observed=d[0]+d[1];
 $display("TRACE enums %0d %s %s %0d %0d",q.size(),last.name(),d[0].name(),a[-2],d[1]);
 end
endmodule
