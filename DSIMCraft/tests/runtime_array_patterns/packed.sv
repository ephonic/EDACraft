module top;
 typedef enum logic[1:0]{RED=1,BLUE=2} color_t;
 typedef struct packed {logic[64:0] data;color_t color;} packet_t;
 packet_t q[$];color_t colors[];logic[66:0] observed;
 initial begin
  q='{'{65'h10000000000000000,RED},'{65'h1ffffffffffffffff,BLUE}};
  colors='{RED,BLUE};observed=q[1];
  if(q.size()!=2||q[0].data!==65'h10000000000000000||q[1].color.name()!="BLUE"||colors[0].name()!="RED")$fatal(1,"typed pattern");
  q[0].data[64]=0;q[0].data[4+:4]=4'ha;q[0].color=BLUE;
  if(q[0].data!==65'h0a0||q[0].color.name()!="BLUE")$fatal(1,"packed container member writes");
  q='{};colors='{};
  #1;$display("TRACE packed %h",observed);$finish;
 end
endmodule
