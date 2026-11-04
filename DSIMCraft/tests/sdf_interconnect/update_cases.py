"""Disambiguate receiver MIPD readback from per-source update state.

These are executable reference studies, not native INTERCONNECT support.
Keep the original thirteen fixtures unchanged.
"""
from pathlib import Path
import json
import shutil
from cases import make as make_base, TRANSITIONS


def make(out):
    out = Path(out)
    basis = out / '_basis'
    originals = make_base(basis)
    cases = {}
    initial = '(ABSOLUTE(INTERCONNECT src/Z fast/A (3))(INTERCONNECT other/Z fast/A (9)))'
    crossed = '(ABSOLUTE(INTERCONNECT src/Z fast/A (3)(10)(6))(INTERCONNECT other/Z fast/A (9)(4)(12)))'

    def entry(source, values):
        return '(INTERCONNECT ' + source + '/Z fast/A ' + values + ')'

    def add(name, entries, question):
        w = out / name
        w.mkdir()
        for filename in ['cells.v', 'cells.lib', 'net.v', 'tb.v']:
            shutil.copyfile(basis / 'multi-driver' / filename, w / filename)
        # Exercise all twelve separated four-state transitions while retaining
        # two actual structural sources at the annotated receiving pin.
        tb = (w / 'tb.v').read_text()
        old = "a=0;b=1'bz;#100;a=1;#100;b=0;#100;a=1'bz;#100;b=1;#100;a=0;#100;b=1'bz;#100;"
        new = "b=1'bz;a=0;#100;" + ''.join('a=' + value + ';#100;' for value in TRANSITIONS[1:])
        assert tb.count(old) == 1
        (w / 'tb.v').write_text(tb.replace(old, new))
        (w / 'delay.sdf').write_text('(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)(CELL(CELLTYPE "dut")(INSTANCE)(DELAY' + entries + ')))\n')
        cases[name] = dict(originals['multi-driver'], question=question)

    for source, label in [('src', 'low'), ('other', 'high')]:
        add('decrement-' + label, initial + '(INCREMENT' + entry(source, '(-7)') + ')',
            'Does decrement read the effective 9ps, and is the other source retained?')
        add('replace-' + label, initial + '(ABSOLUTE' + entry(source, '(4)') + ')',
            'Does a later ABS replace the whole receiver or one source before MAXIMUM?')
        add('increment-then-replace-' + label,
            initial + '(INCREMENT' + entry('src', '(20)') + ')(ABSOLUTE' + entry(source, '(4)') + ')',
            'Is incremented effective 29ps retained when this source is replaced?')
    add('increment-then-decrement-other',
        initial + '(INCREMENT' + entry('src', '(20)') + ')(INCREMENT' + entry('other', '(-7)') + ')',
        'Does second increment replace receiver effective 29ps by 22ps or retain source maximum?')
    add('sparse-absolute', crossed + '(ABSOLUTE' + entry('src', '(5)()(8)') + ')',
        'Do empty tuple positions preserve the source or effective receiver components?')
    add('sparse-increment', crossed + '(INCREMENT' + entry('src', '(20)()(-2)') + ')',
        'Which current components are read, retained, clamped and merged?')
    add('six-values', '(ABSOLUTE' + entry('src', '(3)(7)(11)(13)(17)(19)') + ')',
        'Does six-value MIPD use its first three components or transition-derived reduction?')
    add('typical-corner', '(ABSOLUTE' + entry('src', '(1:3:5)(2:4:6)(7:9:11)') + ')',
        'Are the three TYPICAL components independently selected?')
    add('sparse-corner-increment', crossed + '(INCREMENT' + entry('src', '(20::)(:2:)(::4)') + ')',
        'Does a missing selected corner preserve effective receiver delay or supply a zero increment?')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


if __name__ == '__main__':
    import sys
    make(sys.argv[1])
