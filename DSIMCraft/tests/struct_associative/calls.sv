`timescale 1ps/1ps
module top;
 typedef struct {string label;bit[7:0] flags;logic[3:0] state;int n;} Entry;
 typedef Entry Map[string];Map source,result;Entry returned;int complete=0;
 function automatic Entry transform(input Entry value);
  Map local_values;Entry missing;
  missing=local_values["none"];
  if(missing.label!=""||missing.flags!==0||missing.state!==4'bxxxx||local_values.num()!=0)begin missing.n=-100;return missing;end
  local_values["item"]=value;local_values["item"].label="local";local_values["item"].n+=3;return local_values["item"];
 endfunction
 task automatic change(inout Entry value,output Entry snapshot);
  value.flags='x;value.label="ref";snapshot=value;
 endtask
 task automatic overlap(input int id);
  Map local_values;Entry missing;
  local_values["local"].n=id;local_values["local"].label="private";
  #2;missing=local_values["missing"];
  if(missing.flags!==0||missing.label!=""||local_values.num()!=1||local_values["local"].n!=id)$fatal(1,"independent activation");
  local_values["local"].flags='z;if(local_values["local"].flags!==0)$fatal(1,"activation mask");complete++;
 endtask
 initial begin
  source["item"]='{label:"source",flags:8'hff,state:4'b10xz,n:4};returned=transform(source["item"]);result["item"]=returned;
  if(returned.n!=7||result["item"].label!="local"||result["item"].n!=7||source["item"].label!="source")$fatal(1,"input return copy");
  change(returned,source["item"]);result["item"]=returned;
  if(result["item"].flags!==0||source["item"].label!="ref"||source["item"].state!==4'b10xz)$fatal(1,"ref output copy");
  fork overlap(5);overlap(9);join
  returned=transform(source["item"]);result["item"]=returned;if(result["item"].n!=10||returned.n!=10||complete!=2)$fatal(1,"automatic slot reuse");
  $display("TRACE struct calls %0d",result["item"].n);$finish;
 end
endmodule
