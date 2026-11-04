module top;
 typedef struct {time read_time;time write_time;int unsigned read_count;int unsigned write_count;} Access;
 class Debug;
  Access access[string];
  function void touch(string client);
   if(!access.exists(client))access[client]='{read_time:0,write_time:0,read_count:0,write_count:0};
   access[client].read_count++;access[client].read_time=17;
  endfunction
 endclass
 Debug d;Access record;Access copy[string];int total=0;
 initial begin
  d=new;record='{read_time:3,write_time:5,read_count:7,write_count:11};d.access["client"]=record;
  d.touch("client");d.touch("second");record=d.access["client"];
  if(record.read_count!=8||record.write_count!=11||record.read_time!=17)$fatal(1,"UVM access read/write");
  copy=d.access;copy["client"].write_count=22;
  if(d.access["client"].write_count!=11||d.access.num()!=2)$fatal(1,"map copy isolation");
  foreach(copy[k])total+=copy[k].read_count;
  if(total!=9)$fatal(1,"map iteration");
  $display("TRACE struct access %0d",total);$finish;
 end
endmodule
