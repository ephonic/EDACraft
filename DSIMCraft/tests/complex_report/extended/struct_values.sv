module tb;
  typedef struct {bit [7:0] address;logic [129:0] data;} packet_t;
  packet_t packets[0:1];
  packet_t copy;
  initial begin
    if(packets[0].address!==0||packets[1].address!==0||packets[0].data!==130'bx)$fatal(1,"field defaults");
    packets[0].address=8'hxz;packets[0].data=130'h3abcdef01_23456789_abcdef01_23456789;
    if(packets[0].address!==0)$fatal(1,"two state field conversion");
    packets[1].address=8'h77;packets[1].data=packets[0].data;
    copy=packets[1];
    if(copy.address!==8'h77||copy.data!==packets[0].data||$bits(copy)!=138)$fatal(1,"struct copy/width");
    $display("TRACE structs %h %h %0d",copy.address,copy.data,$bits(copy));$finish;
  end
endmodule
