module top;
 typedef bit [27:0] flags_t;
 typedef enum flags_t {DEFAULT=0, DEEP=1<<16, SHALLOW=1<<17, REFERENCE=1<<18} policy_t;
 typedef policy_t alias_t;
 typedef enum int {NEG=-2,ZERO=0,POS=5} signed_t;
 int policies[alias_t],values[signed_t];policy_t p,policies_found[$];signed_t k,found[$];int count;
 initial begin
  policies[REFERENCE]=33;policies[DEFAULT]=11;policies[DEEP]=22;
  foreach(policies[i])begin
   if($bits(i)!=28)$fatal(1,"enum index width");
   p=i;$display("TRACE policy %s %0d",i.name(),policies[i]);count++;
  end
  if(count!=3||!policies.last(p)||p!=REFERENCE)$fatal(1,"policy traversal");
  policies_found=policies.find_index() with (item>11);
  if(policies_found.size()!=2||policies_found[0]!=DEEP||policies_found[1]!=REFERENCE)$fatal(1,"policy locator");
  values[NEG]=11;values[ZERO]=22;values[5]=33;
  if(values.first(k))do $display("TRACE signed %s %0d",k.name(),values[k]);while(values.next(k));
  found=values.find_index() with (item>20);
  foreach(found[i])$display("TRACE found %s",found[i].name());
  if(values.prev(k)==0||k!=ZERO)$fatal(1,"previous key");
  values.delete(NEG);if(values.exists(NEG)||values.num()!=2)$fatal(1,"delete enum");
 end
endmodule
