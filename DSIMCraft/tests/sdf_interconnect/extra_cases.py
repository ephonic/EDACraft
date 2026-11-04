"""Disambiguate MAXIMUM merging versus ordered updates at a receiving pin."""
from pathlib import Path
import json, shutil
from cases import make as make_base

def make(out):
    out = Path(out); base = out / '_basis'; originals = make_base(base); cases = {}
    def add(name, template, entries):
        w = out / name; w.mkdir()
        for filename in ['cells.v', 'cells.lib', 'net.v', 'tb.v']:
            shutil.copyfile(base / template / filename, w / filename)
        (w / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)(CELL(CELLTYPE "dut")(INSTANCE)(DELAY' + entries + ')))\n')
        cases[name] = dict(originals[template], template=template)
    first = '(INTERCONNECT src/Z fast/A (3)(10)(6))'
    second = '(INTERCONNECT other/Z fast/A (9)(4)(12))'
    add('crossed-sources', 'multi-driver', '(ABSOLUTE' + first + second + ')')
    add('crossed-reversed', 'multi-driver', '(ABSOLUTE' + second + first + ')')
    first = '(INTERCONNECT src/Z fast/A (3)(4)(6))'
    second = '(INTERCONNECT src/Z fast/A (9)(11)(13))'
    add('duplicate-absolute', 'fanout', '(ABSOLUTE' + first + second + ')')
    add('duplicate-reversed', 'fanout', '(ABSOLUTE' + second + first + ')')
    add('increment-two-sources', 'multi-driver', '(ABSOLUTE(INTERCONNECT src/Z fast/A (3))(INTERCONNECT other/Z fast/A (9)))(INCREMENT(INTERCONNECT src/Z fast/A (20)))')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases
