"""Use the independent Python prototype decoder, with libzstd on older Python."""
import ctypes
import ctypes.util
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/waveform'))
import dwf
if dwf.zstd is None:
    lib=ctypes.CDLL(ctypes.util.find_library('zstd'))
    lib.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t]
    lib.ZSTD_decompress.restype=ctypes.c_size_t
    lib.ZSTD_isError.argtypes=[ctypes.c_size_t];lib.ZSTD_isError.restype=ctypes.c_uint
    lib.ZSTD_findFrameCompressedSize.argtypes=[ctypes.c_void_p,ctypes.c_size_t];lib.ZSTD_findFrameCompressedSize.restype=ctypes.c_size_t
    class Decoder:
        eof=False;unused_data=b''
        def decompress(self,data,max_length):
            if lib.ZSTD_findFrameCompressedSize(data,len(data))!=len(data):raise ValueError('invalid single Zstd frame')
            output=ctypes.create_string_buffer(max_length)
            n=lib.ZSTD_decompress(output,max_length,data,len(data))
            if lib.ZSTD_isError(n):raise ValueError('Zstd decoding failed or exceeds output limit')
            self.eof=True
            return output.raw[:n]
    class Zstd:
        ZstdDecompressor=Decoder
    dwf.zstd=Zstd()


def read(path):
    if str(path).endswith('.dwf'):
        with path.open('rb') as f:
            r=dwf.Reader(f);meta,events=r.meta,list(r.events())
    else:
        with path.open() as f:
            meta,stream=dwf.read_vcd_header(f);events=list(dwf.vcd_events(stream,meta))
    # Alias declarations are authoritative in the ordered header. Native META
    # omits the prototype importer's redundant per-signal aliases JSON.
    # VCD assigns dense decoder IDs by first declaration; a native dictionary
    # may allocate IDs before traversing its hierarchy. Canonicalize by code.
    codes=list(dict.fromkeys(t[3] for t in meta['header'] if t[0]=='$var'))
    ranks={code:i for i,code in enumerate(codes)}
    remap=[ranks[s['code']] for s in meta['signals']]
    old={s['code']:s['width'] for s in meta['signals']}
    meta['signals']=[{'code':code,'width':old[code]} for code in codes]
    events=[(t,k,(remap[p[0]],p[1])) if k=='value' else (t,k,p) for t,k,p in events]
    return meta,events


def declarations(meta):
    """Map exact scope components/name/range to value stream ID, without aliases JSON."""
    scope=[];result={};ids={s['code']:i for i,s in enumerate(meta['signals'])}
    for t in meta['header']:
        if t[0]=='$scope':scope.append(t[2].removeprefix('\\'))
        elif t[0]=='$upscope':scope.pop()
        elif t[0]=='$var':
            key=tuple(scope)+(t[4].removeprefix('\\'),)
            assert key not in result,key
            result[key]=(ids[t[3]],int(t[2]),t[5:-1])
    return result


def timeline(meta,events):
    """Settled tick states, suppressing repeated values, retaining each name."""
    streams=[[] for _ in meta['signals']]
    for t,k,p in events:
        if k!='value':continue
        ident,value=p
        if streams[ident] and streams[ident][-1][0]==t:streams[ident][-1]=(t,value)
        else:streams[ident].append((t,value))
    out={}
    for key,(ident,width,ranges) in declarations(meta).items():
        changes=[]
        for t,value in streams[ident]:
            if not changes or changes[-1][1]!=value:changes.append((t,value))
        out[key]=(width,ranges,changes)
    return out


def reference_timeline(meta,events):
    # Icarus omits the explicit [0:0] on a one-bit vector. Keep all nonzero
    # singleton indices/ranges; native metadata is checked separately.
    return {key:(width,[] if width==1 and ranges==['[0:0]'] else ranges,changes)
            for key,(width,ranges,changes) in timeline(meta,events).items()}


def bit_timeline(meta,events):
    """Settled bits, including VCS vectors declared as repeated indexed scalars.

    Keys retain exact scope/name and the declared bit index (None for scalars).
    No values, indices or duplicate bit declarations are silently discarded.
    """
    streams=[[] for _ in meta['signals']]
    for time,kind,payload in events:
        if kind!='value':continue
        ident,value=payload
        if streams[ident] and streams[ident][-1][0]==time:streams[ident][-1]=(time,value)
        else:streams[ident].append((time,value))
    ids={s['code']:i for i,s in enumerate(meta['signals'])};scope=[];result={}
    for token in meta['header']:
        if token[0]=='$scope':scope.append(token[2].removeprefix('\\'))
        elif token[0]=='$upscope':scope.pop()
        elif token[0]=='$var':
            width=int(token[2]);ranges=''.join(token[5:-1]);name=token[4].removeprefix('\\')
            if ranges:
                match=re.fullmatch(r'\[(-?\d+)(?::(-?\d+))?\]',ranges)
                assert match,('unsupported VCD range',ranges)
                left=int(match[1]);right=int(match[2]) if match[2] is not None else left
                assert abs(left-right)+1==width,('VCD range/width mismatch',token)
                indices=[right+(i if left>=right else -i) for i in range(width)]
            else:indices=[None] if width==1 else list(range(width))
            for offset,index in enumerate(indices):
                key=(*scope,name,index);assert key not in result,('duplicate VCD bit',key)
                changes=[]
                for time,(a,b) in streams[ids[token[3]]]:
                    value=((a>>offset)&1,(b>>offset)&1)
                    if not changes or changes[-1][1]!=value:changes.append((time,value))
                result[key]=changes
    return result
