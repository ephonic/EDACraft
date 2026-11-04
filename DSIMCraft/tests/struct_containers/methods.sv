module top;
 typedef struct {string name;int id;} Entry;
 class Holder;Entry values[$:3];endclass
 Holder holder,other;Entry q[$],found[$],v;int observed;
 initial begin
  holder=new;other=new;holder.values.push_back('{name:"z",id:3});holder.values.push_front('{name:"alpha",id:1});holder.values.insert(1,'{name:"m",id:2});
  holder.values.sort with(item.name);if(holder.values[0].name!="alpha"||holder.values[2].name!="z")$fatal(1,"string sort key");
  holder.values.rsort(e) with(e.id);if(holder.values[0].id!=3||holder.values[2].id!=1)$fatal(1,"named sort key");
  q=holder.values;other.values=q;q[0].name="copy";if(holder.values[0].name!="z")$fatal(1,"array copy isolation");
  found=holder.values.find with(item.id>1);if(found.size()!=2||found[0].name!="z"||found[1].name!="m")$fatal(1,"find values");
  found=holder.values.min with(item.id);if(found.size()!=1||found[0].name!="alpha")$fatal(1,"min original element");
  v=other.values.pop_front();if(v.name!="z"||v.id!=3)$fatal(1,"pop struct");other.values.reverse();
  observed=v.id+other.values[0].id;$display("TRACE struct methods %0d",observed);$finish;
 end
endmodule
