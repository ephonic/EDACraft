"""Compare frozen production inputs and complete decoded waves across hosts."""
from pathlib import Path
import hashlib,json,sys
root,mac,linux,out=map(lambda p:Path(p).resolve(),sys.argv[1:5]);sys.path.insert(0,str(root/'tests/waveform'));from reader import read
m=json.loads((mac/'release.json').read_text());l=json.loads((linux/'release/release.json').read_text());assert m['status']==l['status']=='PASS' and m['active'] and l['active']
assert m['git_commit']==l['git_commit'] and m['source_sha256']==l['source_sha256'];assert not m['git_dirty'] and not l['git_dirty']
report=dict(status='RUNNING',source_commit=m['git_commit'],source_sha256=m['source_sha256'],cpp_files=0,complete_waveforms=0,actual_entry_models=0,models={})
try:
 for group in ['virtual_interfaces','stream_targets','stream_enum_casts']:
  a=json.loads((mac/group/'results.json').read_text());b=json.loads((linux/'release'/group/'results.json').read_text());assert a['status']==b['status']=='PASS';assert a['captures']==b['captures'];assert a['negative_cases']==b['negative_cases'];assert a['runtime_rejections']==b['runtime_rejections']
  for name,x in a['models'].items():
   y=b['models'][name];assert x['trace']==y['trace'] and x['source_sha256']==y['source_sha256']
   for mode in ['serial','shared','wheel']:
    mp=mac/group/name/(mode+'.cpp');lp=linux/'release'/group/name/(mode+'.cpp');assert mp.read_bytes()==lp.read_bytes(),(group,name,mode,'complete CPP')
    assert read(mac/group/name/(mode+'.vcd'))==read(linux/'release'/group/name/(mode+'.vcd')),(group,name,mode,'complete decoded waveform')
    report['cpp_files']+=1;report['complete_waveforms']+=1
   report['models'][group+'/'+name]=dict(trace=x['trace'],source_sha256=x['source_sha256'])
 ma=json.loads((out.parent/'mac-entry/results.json').read_text());la=json.loads((linux/'entry/results.json').read_text());assert ma['status']==la['status']=='PASS';assert ma['source_commit']==la['source_commit']==report['source_commit']
 for name,x in ma['models'].items():
  y=la['models'][name];assert x['trace']==y['trace'] and x['cpp_sha256']==y['cpp_sha256'];assert x['complete_waveform_identity'] and y['complete_waveform_identity']
  assert read(out.parent/'mac-entry'/name/'entry.vcd')==read(linux/'entry'/name/'entry.vcd'),(name,'actual entry complete wave')
  report['actual_entry_models']+=1
 report.update(status='PASS',mac_release=str(mac),linux_release=l['release'])
finally:out.write_text(json.dumps(report,indent=2)+'\n')
print('PASS cross-host:',report['cpp_files'],'complete CPP files,',report['complete_waveforms'],'complete waves,',report['actual_entry_models'],'actual-entry models')
