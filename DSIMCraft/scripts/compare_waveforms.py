#!/usr/bin/env python3
"""Compare complete ordered digital VCD/DWF streams without retaining history."""
import argparse
from contextlib import ExitStack
import io
from itertools import zip_longest
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments/waveform'))
import dwf


def _identity(stat):
    return (stat.st_dev,stat.st_ino,stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns)


def _dictionary(meta):
    """Preserve declarations and alias groups, independently of identifier codes."""
    signals=meta['signals'];codes={s['code']:i for i,s in enumerate(signals)}
    if len(codes)!=len(signals):raise ValueError('duplicate signal codes')
    groups=[[] for _ in signals];scope=[];scopes=set();names=set();scales=[];ended=False
    for token in meta['header']:
        if ended:raise ValueError('header tokens after enddefinitions')
        if not token or token[-1]!='$end':raise ValueError('invalid header directive')
        kind=token[0]
        if kind=='$scope':
            if len(token)!=4:raise ValueError('invalid scope declaration')
            scope.append(token[2].removeprefix('\\'));scopes.add((tuple(scope),token[1]))
        elif kind=='$upscope':
            if len(token)!=2 or not scope:raise ValueError('unbalanced waveform scope')
            scope.pop()
        elif kind=='$var':
            if len(token)<6 or token[3] not in codes:raise ValueError('invalid signal declaration')
            width=int(token[2]);ident=codes[token[3]]
            if width!=signals[ident]['width'] or not 1<=width<=dwf.MAX_BITS:raise ValueError('declaration width mismatch')
            if token[1] not in {'wire','reg','logic','bit','integer','parameter','time','supply0','supply1',
                                 'tri','triand','trior','trireg','tri0','tri1','wand','wor'}:
                raise ValueError('only persistent digital signals supported')
            name=token[4].removeprefix('\\');packed=''.join(token[5:-1]);key=(tuple(scope),name,packed)
            if key in names:raise ValueError('duplicate waveform declaration')
            if packed:
                match=re.fullmatch(r'\[(-?\d+)(?::(-?\d+))?\]',packed)
                if not match:raise ValueError('unsupported packed declaration range')
                left=int(match[1]);right=int(match[2]) if match[2] is not None else left
                if abs(left-right)+1!=width:raise ValueError('declaration range/width mismatch')
            names.add(key);groups[ident].append((tuple(scope),name,token[1],width,packed))
        elif kind=='$timescale':
            match=re.fullmatch(r'(1|10|100)(s|ms|us|ns|ps|fs)',''.join(token[1:-1]))
            if not match:raise ValueError('unsupported waveform timescale')
            scales.append(int(match[1])*dict(s=10**15,ms=10**12,us=10**9,ns=10**6,ps=1000,fs=1)[match[2]])
        elif kind=='$enddefinitions':
            if len(token)!=2 or scope:raise ValueError('unclosed waveform scope')
            ended=True
        elif kind not in ('$date','$version','$comment'):
            raise ValueError('unsupported waveform header directive')
    if not ended or len(scales)!=1:raise ValueError('exactly one timescale and enddefinitions required')
    if any(not g for g in groups):raise ValueError('signal has no declaration')
    ordered=sorted((tuple(sorted(g)),i) for i,g in enumerate(groups))
    remap=[0]*len(groups)
    for rank,(_,ident) in enumerate(ordered):remap[ident]=rank
    return (tuple(sorted(scopes)),tuple(g for g,_ in ordered)),remap,scales[0],len(names)


def _open(stack,path):
    binary=stack.enter_context(path.open('rb'));before=_identity(os.fstat(binary.fileno()))
    magic=binary.read(len(dwf.MAGIC));binary.seek(0)
    if magic==dwf.MAGIC:
        reader=dwf.Reader(binary);meta,events,fmt=reader.meta,reader.events(),'dwf'
    else:
        text=stack.enter_context(io.TextIOWrapper(binary,encoding='utf-8'))
        meta,tokens=dwf.read_vcd_header(text);events,fmt=dwf.vcd_events(tokens,meta),'vcd'
    shape,remap,tick,declarations=_dictionary(meta)
    return binary,before,shape,remap,tick,declarations,events,fmt


def _events(events,remap,tick):
    for time,kind,payload in events:
        if kind=='value':payload=(remap[payload[0]],payload[1])
        elif kind=='control':payload=tuple(payload)
        yield time*tick,kind,payload


def _brief(event):
    if event is None:return 'end of stream'
    time,kind,payload=event
    if kind=='value':
        ident,(a,b)=payload
        return f't={time}fs value stream={ident} aval={hex(a)[:96]} bval={hex(b)[:96]}'
    return f't={time}fs {kind} {str(payload)[:160]}'


def compare(left,right):
    """Keep two dictionaries/indices and decoder blocks, never an event history.

    Version/date/header comments and identifier codes may differ. Hierarchy,
    variable types, widths, ranges and alias grouping must match. Every time
    marker, control and four-state transition is compared at physical time.
    """
    left,right=Path(left).resolve(),Path(right).resolve()
    with ExitStack() as stack:
        a,b=_open(stack,left),_open(stack,right)
        if a[2]!=b[2]:raise ValueError('waveform declarations, hierarchy or alias groups differ')
        absent=object();counts=dict(time=0,value=0,control=0);last=None;total=0
        for i,(x,y) in enumerate(zip_longest(_events(a[6],a[3],a[4]),_events(b[6],b[3],b[4]),fillvalue=absent)):
            if x!=y:
                raise ValueError(f'event {i} differs: left {_brief(None if x is absent else x)}; right {_brief(None if y is absent else y)}')
            total+=1;counts[x[1]]+=1;last=x[0]
        for path,entry in [(left,a),(right,b)]:
            if _identity(os.fstat(entry[0].fileno()))!=entry[1] or _identity(path.stat())!=entry[1]:
                raise ValueError('waveform input changed during comparison')
        return dict(status='PASS',comparison='ordered-events',signals=len(a[3]),declarations=a[5],events=total,
            event_counts=counts,last_time_fs=last,formats=[a[7],b[7]],
            inputs=[dict(path=str(p),bytes=e[1][2]) for p,e in [(left,a),(right,b)]])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left',type=Path);parser.add_argument('right',type=Path)
    parser.add_argument('--output',type=Path,help='Create a new JSON report; existing files are protected.')
    args=parser.parse_args()
    try:report=compare(args.left,args.right)
    except (ValueError,OSError,UnicodeError) as error:report=dict(status='FAIL',error=str(error))
    if args.output:
        try:
            with args.output.open('x') as out:out.write(json.dumps(report,indent=2)+'\n')
        except OSError as error:
            print(json.dumps(dict(status='FAIL',error='cannot create comparison report: '+str(error))))
            return 1
    print(json.dumps(report,indent=2))
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
