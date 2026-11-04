"""Separate structural source count from the number of annotated sources."""
from pathlib import Path
import json
import shutil
from cases import make as make_base, TRANSITIONS


def make(out):
    out = Path(out)
    basis = out / '_basis'
    originals = make_base(basis)
    cases = {}
    replace = '(ABSOLUTE(INTERCONNECT src/Z fast/A (9)))(ABSOLUTE(INTERCONNECT src/Z fast/A (3)))'
    increment = '(ABSOLUTE(INTERCONNECT src/Z fast/A (3)))(INCREMENT(INTERCONNECT src/Z fast/A (20)))(ABSOLUTE(INTERCONNECT src/Z fast/A (4)))'
    for template, prefix in [('fanout', 'single'), ('multi-driver', 'multiple')]:
        for suffix, entries in [('repeat-absolute', replace), ('increment-replace', increment)]:
            name = prefix + '-' + suffix
            w = out / name
            w.mkdir()
            for filename in ['cells.v', 'cells.lib', 'net.v', 'tb.v']:
                shutil.copyfile(basis / template / filename, w / filename)
            if template == 'multi-driver':
                tb = (w / 'tb.v').read_text()
                old = "a=0;b=1'bz;#100;a=1;#100;b=0;#100;a=1'bz;#100;b=1;#100;a=0;#100;b=1'bz;#100;"
                new = "b=1'bz;a=0;#100;" + ''.join('a=' + value + ';#100;' for value in TRANSITIONS[1:])
                assert tb.count(old) == 1
                (w / 'tb.v').write_text(tb.replace(old, new))
            (w / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)(CELL(CELLTYPE "dut")(INSTANCE)(DELAY' + entries + ')))\n')
            cases[name] = dict(originals[template], annotated_sources=1,
                question='Does repeated ABS readback depend on physical source multiplicity even when only src/Z is annotated?')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


if __name__ == '__main__':
    import sys
    make(sys.argv[1])
