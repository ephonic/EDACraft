"""Full stream identity, alias/ID semantics, corruption and history-memory growth."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess
import sys
import tracemalloc

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_waveforms import compare,dwf

out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
header=[['$version','independent-fixture','$end'],['$timescale','1ps','$end'],
    ['$scope','module','top','$end'],['$var','reg','8','a','data','[7:0]','$end'],
    ['$var','wire','8','a','alias','[7:0]','$end'],['$var','reg','257','b','wide','[256:0]','$end'],
    ['$var','wire','1','c','flag','$end'],['$scope','module','child','$end'],
    ['$var','wire','8','a','copy','[7:0]','$end'],['$upscope','$end'],['$upscope','$end'],['$enddefinitions','$end']]
meta=dict(schema='dsim.wave.prototype.v1',header=header,signals=[dict(code='a',width=8),dict(code='b',width=257),dict(code='c',width=1)])
events=[(0,'time',None),(0,'control',['$dumpvars']),(0,'value',(0,(0,0))),
    (0,'value',(1,((1<<256)+23,1<<129))),(0,'value',(2,(0,1))),(0,'control',['$end']),
    (5,'time',None),(5,'value',(0,(0x95,0x31))),(5,'value',(0,(0x33,0x23))),
    (5,'time',None),(5,'control',['$comment','kept','$end']),
    (5,'control',['$dumpoff']),(5,'value',(0,(255,255))),(5,'control',['$end']),
    (8,'time',None),(8,'control',['$dumpon']),(8,'value',(2,(1,0))),(8,'control',['$end'])]

def write_vcd(path,dictionary,stream):
    with path.open('w') as f:
        for token in dictionary['header']:f.write(' '.join(token)+'\n')
        for time,kind,payload in stream:
            if kind=='time':f.write('#'+str(time)+'\n')
            elif kind=='control':f.write(' '.join(payload)+'\n')
            else:
                ident,(a,b)=payload;signal=dictionary['signals'][ident];width=signal['width']
                bits=''.join(('x' if (a>>i)&1 else 'z') if (b>>i)&1 else str((a>>i)&1) for i in reversed(range(width)))
                f.write((bits if width==1 else 'b'+bits+' ')+signal['code']+'\n')

def write_dwf(path,dictionary,stream,codec='raw',block=3):
    with path.open('wb') as f:
        writer=dwf.Writer(f,dictionary,codec,block)
        for event in stream:writer.append(event)
        writer.close()

def reject(left,right,part):
    try:compare(left,right)
    except ValueError as error:assert part in str(error),(part,str(error));return
    raise AssertionError(('expected rejection',left,right))

left=out/'oracle.vcd';write_vcd(left,meta,events)
codecs=['raw','zlib']+(['zstd'] if dwf.zstd is not None else [])
for codec in codecs:
    path=out/(codec+'.dwf');write_dwf(path,meta,events,codec)
    result=compare(left,path);assert result['events']==len(events) and result['signals']==3 and result['declarations']==5
    assert result['last_time_fs']==8000

# Rename codes, reorder dictionary IDs/declarations, and change tick units.
other=copy.deepcopy(meta);rename={'a':'signalA','b':'longBus','c':'flagCode'}
for token in other['header']:
    if token[0]=='$var':token[3]=rename[token[3]]
    if token[0]=='$timescale':token[1]='1fs'
    if token[0]=='$version':token[1]='another-writer'
other['header'][3],other['header'][4]=other['header'][4],other['header'][3]
other['signals']=[dict(code=rename[s['code']],width=s['width']) for s in reversed(meta['signals'])]
remapped=[(t*1000,k,(2-p[0],p[1]) if k=='value' else p) for t,k,p in events]
write_dwf(out/'remapped.dwf',other,remapped,'raw',2)
assert compare(left,out/'remapped.dwf')['events']==len(events)
write_vcd(out/'remapped.vcd',other,remapped)
assert compare(out/'remapped.vcd',out/'remapped.dwf')['events']==len(events)

changed=list(events);changed[3]=(0,'value',(1,((1<<256)+23,1<<130)))
write_dwf(out/'changed.dwf',meta,changed);reject(left,out/'changed.dwf','event 3 differs')
write_dwf(out/'extra-time.dwf',meta,[*events,(8,'time',None)])
reject(left,out/'extra-time.dwf','end of stream')
write_dwf(out/'short.dwf',meta,events[:-1]);reject(left,out/'short.dwf','end of stream')
changed_meta=copy.deepcopy(meta);changed_meta['signals'].append(dict(code='d',width=8))
changed_meta['header'][4][3]='d';write_dwf(out/'lost-alias.dwf',changed_meta,events)
reject(left,out/'lost-alias.dwf','alias groups differ')
changed_meta=copy.deepcopy(meta);changed_meta['header'][3][5]='[8:0]'
write_dwf(out/'invalid-range.dwf',changed_meta,events);reject(left,out/'invalid-range.dwf','range/width mismatch')
damaged=bytearray((out/'raw.dwf').read_bytes());damaged[-1]^=1
(out/'bad-footer.dwf').write_bytes(damaged);reject(left,out/'bad-footer.dwf','index')
damaged=bytearray((out/'raw.dwf').read_bytes());position=damaged.index(b'BLK1')+dwf.RECORD.size+5;damaged[position]^=1
(out/'bad-crc.dwf').write_bytes(damaged);reject(left,out/'bad-crc.dwf','checksum')
(out/'truncated.dwf').write_bytes((out/'raw.dwf').read_bytes()[:-9]);reject(left,out/'truncated.dwf','index')
# Changing a source even without adding events must invalidate the result.
mutable=out/'mutating.vcd';mutable.write_bytes(left.read_bytes())
original=dwf.vcd_events;mutated=False
def mutate(stream,dictionary):
    global mutated
    for event in original(stream,dictionary):
        if not mutated:
            mutated=True
            with mutable.open('a') as f:f.write('\n')
        yield event
dwf.vcd_events=mutate
try:reject(left,mutable,'changed during comparison')
finally:dwf.vcd_events=original
before=hashlib.sha256(left.read_bytes()).hexdigest()
result=subprocess.run([sys.executable,ROOT/'scripts/compare_waveforms.py',left,out/'raw.dwf','--output',left],text=True,capture_output=True)
assert result.returncode!=0 and hashlib.sha256(left.read_bytes()).hexdigest()==before
(out/'cli.json').unlink(missing_ok=True)
result=subprocess.run([sys.executable,ROOT/'scripts/compare_waveforms.py',left,out/'raw.dwf','--output',out/'cli.json'],text=True,capture_output=True)
assert result.returncode==0 and json.loads((out/'cli.json').read_text())['events']==len(events)

# Increase history tenfold while keeping dictionary/block size fixed. Neither
# comparator side may retain the history; index storage is allowed to grow.
peaks=[]
for count in [12000,120000]:
    def stream():
        yield (0,'time',None)
        for i in range(count):
            yield (i,'time',None)
            yield (i,'value',(0,(i&255,(i>>4)&255)))
    vcd=out/f'history-{count}.vcd';binary=out/f'history-{count}.dwf'
    write_vcd(vcd,meta,stream());write_dwf(binary,meta,stream(),'raw',1024)
    tracemalloc.start()
    result=compare(vcd,binary)
    _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();peaks.append(peak)
    assert result['events']==1+count*2 and peak<16*1024*1024,(count,peak)
assert peaks[1]<peaks[0]*3+4*1024*1024,peaks
report=dict(status='PASS',codecs=codecs,oracle_events=len(events),full_ordered_events=True,
    hierarchy_aliases_and_id_remap=True,corruption_rejected=True,no_clobber=True,input_mutation_rejected=True,
    history_values=[12000,120000],tracemalloc_peak_bytes=peaks)
(out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
