"""Read every logical signal after natural completion without coupling RTL lanes."""
import json

def instrument(code,ir):
 parallel=ir.get('parallel',{}).get('partitions',1)>1
 marker='\nengine.run();\n' if parallel else '\ns.run();\n'
 assert code.count(marker)==1
 signals=range(ir['signal_count']);owners=ir.get('parallel',{}).get('signal_owner',[])
 rows=[]
 for ident,signal in enumerate(signals):
  get=('engine.kernel('+str(owners[ident])+').get(sid['+str(ident)+'])') if parallel else ('s.get('+str(ident)+')')
  rows.append('{auto value='+get+';std::cout<<"STATE '+str(ident)+' "<<value.a<<":"<<value.b<<":"<<value.w<<"\\n";}')
 return code.replace(marker,marker+'\n'.join(rows)+'\n')
