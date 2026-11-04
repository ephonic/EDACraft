typedef struct {bit [3:0] known;logic [3:0] four;} pair_t;
class Box;pair_t data[];endclass
module top;
 Box box;int stage=0;
 function automatic void fill(ref pair_t data[]);
  data=new[2];data[0].known=4'hx;data[0].four=4'hz;data[1]='{4'ha,4'h5};
 endfunction
 initial begin
  box=new();fill(box.data);stage++;#1;
  $display("TRACE struct %h %h %h %h",box.data[0].known,box.data[0].four,box.data[1].known,box.data[1].four);$finish;
 end
endmodule
