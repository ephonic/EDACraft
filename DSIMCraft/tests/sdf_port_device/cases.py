"""PORT/DEVICE inputs paired with explicit, previously supported annotations.

Equivalence controls are not new VCS evidence. In particular mixed PORT/IC
precedence must also be checked on VCS before claiming vendor compatibility.
"""
from pathlib import Path
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
FILES = ['cells.v', 'cells.lib', 'net.v', 'tb.v', 'delay.sdf']


def fixtures(name, source, destination):
    spec = importlib.util.spec_from_file_location(name, ROOT / source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make(destination)


def wrap(entries, instance='u0', cell='CELL'):
    return ('(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)'
            f'(CELL(CELLTYPE "{cell}")(INSTANCE {instance})(DELAY {entries})))\n')


def make(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    fixtures('port_ic', 'tests/sdf_interconnect/cases.py', out / 'source/ic')
    fixtures('device_path', 'tests/sdf_runtime/cases.py', out / 'source/path')
    fixtures('device_condition', 'tests/sdf_conditional/cases.py', out / 'source/condition')
    cases = {}

    def add(name, family, source, candidate=None, equivalent=None, **meta):
        work = out / name; work.mkdir(exist_ok=True)
        for filename in FILES:
            shutil.copyfile(out / 'source' / family / source / filename, work / filename)
        original = (work / 'delay.sdf').read_text()
        (work / 'delay.sdf').write_text(candidate if candidate is not None else original)
        (work / 'equivalent.sdf').write_text(equivalent if equivalent is not None else original)
        cases[name] = dict(family=family, source=source, **meta)
        return work

    for name in ['fanout', 'twelve', 'pulses', 'destination-precision', 'increment', 'input-and-output']:
        original = (out / 'source/ic' / name / 'delay.sdf').read_text()
        port = re.sub(r'\(INTERCONNECT\s+\S+\s+', '(PORT ', original)
        add('port-' + name, 'ic', name, port, oracle='interconnect-' + name)
    # Explicit leaf CELL scope, wildcard receivers, and min/typ/max selection.
    leaf = ('(DELAYFILE(SDFVERSION "3.0")(TIMESCALE 1ps)'
            '(CELL(CELLTYPE "D")(INSTANCE *)(DELAY(ABSOLUTE(PORT A (3:7:11)(4:8:12))))))\n')
    # Identical S/D definitions are merged by VCS. Wildcard PORT therefore
    # annotates the source input too; explicit IC endpoints form the control.
    control = wrap('(ABSOLUTE(INTERCONNECT a src/A (3:7:11)(4:8:12))'
                   '(INTERCONNECT src/Z fast/A (3:7:11)(4:8:12))'
                   '(INTERCONNECT src/Z slow/A (3:7:11)(4:8:12)))', '', 'dut')
    add('port-wildcard-corners', 'ic', 'fanout', leaf, control, corners=['min', 'typ', 'max'])
    # PORT is one receiving-pin delay, independent of the number of net drivers.
    add('port-multi-driver', 'ic', 'multi-driver',
        wrap('(ABSOLUTE(PORT fast/A (9))(PORT slow/A (13)))', '', 'dut'),
        wrap('(ABSOLUTE(INTERCONNECT src/Z fast/A (9))(INTERCONNECT src/Z slow/A (13)))', '', 'dut'),
        oracle='interconnect-multi-driver')
    add('port-last-update', 'ic', 'multi-driver',
        wrap('(ABSOLUTE(PORT fast/A (9))(PORT fast/A (3))(PORT slow/A (5)))', '', 'dut'),
        wrap('(ABSOLUTE(INTERCONNECT src/Z fast/A (9))(INTERCONNECT src/Z slow/A (5)))', '', 'dut'))
    # Fresh VCS probes distinguish resolved-input MAXIMUM from ordinary
    # last-update behavior, in both leaf and parent annotation scopes.
    add('port-single-last-update', 'ic', 'fanout',
        wrap('(ABSOLUTE(PORT fast/A (9))(PORT fast/A (3)))', '', 'dut'),
        wrap('(ABSOLUTE(INTERCONNECT src/Z fast/A (3)))', '', 'dut'))
    add('port-multi-leaf-last-update', 'ic', 'multi-driver',
        wrap('(ABSOLUTE(PORT A (9))(PORT A (3)))', 'fast', 'D'),
        wrap('(ABSOLUTE(INTERCONNECT src/Z fast/A (9)))', '', 'dut'))
    add('port-multi-reverse-update', 'ic', 'multi-driver',
        wrap('(ABSOLUTE(PORT fast/A (3))(PORT fast/A (9)))', '', 'dut'),
        wrap('(ABSOLUTE(INTERCONNECT src/Z fast/A (9)))', '', 'dut'))
    for order in ['port-first', 'port-last']:
        entries = ['(PORT fast/A (7))', '(INTERCONNECT src/Z fast/A (11))']
        if order == 'port-last': entries.reverse()
        final = 11 if order == 'port-first' else 7
        add('mixed-' + order, 'ic', 'fanout',
            wrap('(ABSOLUTE' + ''.join(entries) + ')', '', 'dut'),
            wrap(f'(ABSOLUTE(INTERCONNECT src/Z fast/A ({final})))', '', 'dut'),
            precedence_pending_vcs=True)
    # One module path per output: frozen IOPATH oracle remains applicable.
    for name in ['twelve', 'pulses', 'two-drivers', 'ff', 'edge-filter', 'independent']:
        original = (out / 'source/path' / name / 'delay.sdf').read_text()
        device = re.sub(r'\(IOPATH\s+(?:\([^)]*\)|\S+)\s+(\S+)\s+', r'(DEVICE \1 ', original)
        add('device-' + name, 'path', name, device, oracle='path-' + name)
    # Named output updates every matching input path; bare DEVICE covers all
    # external outputs, including flop models with private internal state pins.
    add('device-named-outputs', 'path', 'multiple',
        wrap('(ABSOLUTE(DEVICE Z (7))(DEVICE W (19)))'),
        wrap('(ABSOLUTE(IOPATH A Z (7))(IOPATH B Z (7))(IOPATH A W (19))(IOPATH B W (19)))'))
    add('device-all-outputs', 'path', 'multiple',
        wrap('(ABSOLUTE(DEVICE (13)))'),
        wrap('(ABSOLUTE(IOPATH A Z (13))(IOPATH B Z (13))(IOPATH A W (13))(IOPATH B W (13)))'))
    add('device-flop-all', 'path', 'ff', wrap('(ABSOLUTE(DEVICE (7)))'),
        wrap('(ABSOLUTE(IOPATH (posedge A) Z (7)))'), oracle='path-ff')
    add('device-full-path', 'path', 'full', wrap('(ABSOLUTE(DEVICE Z (7)))'),
        wrap('(ABSOLUTE(IOPATH A Z (7))(IOPATH B Z (7)))'))
    for name in ['truth', 'edge', 'output-state']:
        original = (out / 'source/condition' / name / 'delay.sdf').read_text()
        # Keep distinct conditional declarations but annotate them uniformly.
        equivalent = re.sub(r'\(7\)(?:\s*\(11\))?|\(19\)(?:\s*\(23\))?', '(13)', original)
        candidate = ('(DELAYFILE(SDFVERSION "3.0")(TIMESCALE 1ps)'
                     '(CELL(CELLTYPE "CELL")(INSTANCE *)(DELAY(ABSOLUTE(DEVICE Z (13))))))\n')
        add('device-condition-' + name, 'condition', name, candidate, equivalent)
    for order in ['device-first', 'device-last']:
        entries = ['(DEVICE Z (7))', '(IOPATH A Z (19))']
        if order == 'device-last': entries.reverse()
        value = 19
        add('update-' + order, 'path', 'pulses', wrap('(ABSOLUTE' + ''.join(entries) + ')'),
            wrap(f'(ABSOLUTE(IOPATH A Z ({value})))'))
    add('device-increment-corners', 'path', 'pulses',
        wrap('(ABSOLUTE(DEVICE Z (3:7:11)))(INCREMENT(DEVICE Z (-1:2:4)))'),
        wrap('(ABSOLUTE(IOPATH A Z (3:7:11)))(INCREMENT(IOPATH A Z (-1:2:4)))'),
        corners=['min', 'typ', 'max'])
    # Pending input timer and output-path timer coexist across replay boundaries.
    add('port-and-device', 'ic', 'pulses',
        '(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)'
        '(CELL(CELLTYPE "dut")(INSTANCE)(DELAY(ABSOLUTE(PORT fast/A (7)(19))(PORT slow/A (11)(23)))))'
        '(CELL(CELLTYPE "D")(INSTANCE *)(DELAY(ABSOLUTE(DEVICE Z (13))))))\n',
        '(DELAYFILE(SDFVERSION "3.0")(DIVIDER /)(TIMESCALE 1ps)'
        '(CELL(CELLTYPE "dut")(INSTANCE)(DELAY(ABSOLUTE(INTERCONNECT src/Z fast/A (7)(19))(INTERCONNECT src/Z slow/A (11)(23)))))'
        '(CELL(CELLTYPE "D")(INSTANCE *)(DELAY(ABSOLUTE(IOPATH A Z (13))))))\n')
    (out / 'cases.json').write_text(json.dumps(cases, indent=2) + '\n')
    return cases


if __name__ == '__main__':
    import sys
    make(sys.argv[1])
