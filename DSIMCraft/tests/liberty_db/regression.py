#!/usr/bin/env python3
"""Native DB container/diagnostics and unchanged text-Liberty gate execution."""
from pathlib import Path
import gzip,json,random,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]
MAGIC=bytes.fromhex('031710630040ff03')+bytes(248)
def token(s):
    b=s.encode();assert len(b)<256;return bytes([len(b)])+b
def array(marker,values):
    return bytes(marker)+bytes([len(values)])+struct.pack('>'+str(len(values))+'f',*values)
def fixtures():
    root=token('db library name')+b'\x00'+token('#dsim_fixture')+token('root_version')+token('native-test')
    table=token('cell_rise')+array([0x22,3],[.25,.5])+array([0x22,3],[1,2])+array([0x82,2,3],[3,4,5,6])
    compact=array([0x22,3],[.25,.5])+array([0x22,3],[1,2])+array([0x82,2,3],[7,8,9,10])
    cell=token('TESTBWP6T16P96CPD')+token('area')+struct.pack('>f',.125)+token('cell_footprint')+b'\x00'+token('TEST')
    dictionary=b'\x05\x01'+token('version')+b'\x05\x81\x01'+token('contents')
    return [dictionary,table,compact,cell,root]
def run(args,ok=True):
    p=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=120)
    if ok and p.returncode:raise RuntimeError((args,p.stdout,p.stderr))
    if not ok:assert p.returncode,(args,p.stdout,p.stderr)
    return p

def main():
    compiler=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve();out.mkdir(parents=True,exist_ok=True)
    binary=MAGIC+b''.join(gzip.compress(x,mtime=0) for x in fixtures())
    disguised=out/'native.lib';disguised.write_bytes(binary)
    document=json.loads(run([compiler,'--liberty-db-info',disguised]).stdout)
    assert document['reader']=='native' and not document['simulation_model_complete']
    assert document['library_name']=='dsim_fixture' and document['streams']==5
    assert document['dictionary_records_recovered']==2,document
    assert document['tables_recovered']==2 and document['table_values_recovered']==8,document
    assert document['cells_recovered']==1 and document['cells'][0]['area']==.125,document
    assert document['partial_streams']==0
    # A gzip member with a damaged CRC is explicitly partial. A substantial
    # recovered fragment must not prevent finding the following valid ROOT.
    fragment=bytearray(gzip.compress(b'X'*8192,mtime=0));fragment[-8]^=0x80
    fragmented=out/'partial.db';fragmented.write_bytes(MAGIC+fragment+gzip.compress(fixtures()[-1],mtime=0))
    partial=json.loads(run([compiler,'--liberty-db-info',fragmented]).stdout)
    assert partial['partial_streams']==1 and partial['streams']==2,partial
    failures={
        'empty':b'', 'magic-only':MAGIC[:8], 'header-only':MAGIC,
        'plain-gzip':gzip.compress(fixtures()[-1]),
        'no-root':MAGIC+gzip.compress(b'version'),
        'truncated-member':MAGIC+gzip.compress(fixtures()[-1])[:14],
        'random':MAGIC+random.Random(17).randbytes(1000),
    }
    for name,data in failures.items():
        file=out/(name+'.db');file.write_bytes(data)
        p=run([compiler,'--liberty-db-info',file],False)
        assert p.stderr and not p.stdout,(name,p.stdout,p.stderr)
    # Names/extensions cannot send binary DB into the text parser. No output
    # is generated from an incomplete native graph.
    for file in [disguised,fragmented]:
        target=out/(file.stem+'.cpp');target.unlink(missing_ok=True)
        p=run([compiler,'--gate-check','--gate-netlist',ROOT/'tests/gate/four_state.net.v','--gate-top','dut','--liberty',file],False)
        assert 'native Synopsys DB model incomplete' in p.stderr,p.stderr
        assert not target.exists()
    # Text content named .db still compiles and runs the real gate model.
    text=out/'text.db';text.write_text('// content detection\n'+(ROOT/'tests/gate/cells.lib').read_text())
    sim=out/'text-sim';run([compiler,'--gate-netlist',ROOT/'tests/gate/four_state.net.v','--gate-top','dut','--liberty',text,ROOT/'tests/gate/four_state.tb.v','-o',sim])
    expected=json.loads((ROOT/'tests/gate/four_state.expected.json').read_text())
    actual=[x for x in run([sim]).stdout.splitlines() if x.startswith('TRACE ')]
    assert actual==expected,(actual,expected)
    result={'status':'PASS','native_object_extraction':document,'partial_stream_recovery':partial,'malformed_inputs':list(failures),'text_gate_execution':'PASS','incomplete_models_rejected':2}
    (out/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS native DB extraction, CRC/fragment recovery, malformed inputs, strict model guard, text gate simulation')
if __name__=='__main__':main()
