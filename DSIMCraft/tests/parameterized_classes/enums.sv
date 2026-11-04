module top;
 typedef enum logic[64:0] {FIRST=1,LAST=65'h1ffffffffffffffff} E;
 typedef struct packed {logic[64:0] payload;logic[2:0] flags;} Packet;
 class C#(type T=int);T value;function new(T n);value=n;endfunction function T get();return value;endfunction endclass
 C#(E) a;C#(Packet) b;E state;Packet packet;logic[67:0] observed;
 initial begin a=new(LAST);packet.payload='1;packet.flags=5;b=new(packet);state=a.get();observed=b.get();$display("TRACE enums %s %h",state.name(),observed);end
endmodule
