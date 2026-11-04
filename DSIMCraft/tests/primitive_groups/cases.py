"""Scalar primitive groups with an independent four-state truth oracle."""
from itertools import product

VALUES = ['0', '1', 'x', 'z']
KINDS = ['and', 'nand', 'or', 'nor', 'xor', 'xnor', 'buf', 'not',
         'bufif0', 'bufif1', 'notif0', 'notif1']


def invert(value):
    return {'0': '1', '1': '0'}.get(value, 'x')


def binary(kind, a, b):
    if kind == 'and': return '0' if '0' in [a,b] else '1' if a == b == '1' else 'x'
    if kind == 'or': return '1' if '1' in [a,b] else '0' if a == b == '0' else 'x'
    return str(int(a) ^ int(b)) if a in '01' and b in '01' else 'x'


def evaluate(kind, data, control):
    if kind in ['buf', 'not']:
        value = data if data in '01' else 'x'
        return invert(value) if kind == 'not' else value
    if kind.startswith(('bufif', 'notif')):
        value = data if data in '01' else 'x'
        if kind.startswith('not'): value = invert(value)
        enabled = '0' if kind.endswith('0') else '1'
        if control in '01': return value if control == enabled else 'z'
        return 'x'
    base = {'nand': 'and', 'nor': 'or', 'xnor': 'xor'}.get(kind, kind)
    value = binary(base, data, control)
    return invert(value) if kind in ['nand', 'nor', 'xnor'] else value


def make(kind, variant, delay=False):
    assert variant in ['named', 'unnamed', 'mixed']
    terminals = ['q[0],a', 'q[1],b', '{q[2]},~a']
    if kind not in ['buf', 'not']: terminals = [s + ',b' for s in terminals]
    instances = []
    for i, ports in enumerate(terminals):
        name = f'g{i}' if variant == 'named' or variant == 'mixed' and i == 1 else ''
        instances.append(name + '(' + ports + ')')
    # Use both bare and parenthesized delay forms at the instance-list boundary.
    timing = ('#(2,3,4)' if kind.startswith(('bufif', 'notif')) else '#(2,3)') if delay else ''
    if delay and kind == 'buf': timing = '#2'
    if delay and kind == 'not': timing = '#D'
    code = '`timescale 1ps/1ps\nmodule top; parameter D=2; reg a,b;wire [2:0] q;\n'
    code += kind + ' ' + timing + ' ' + ','.join(instances) + ';\ninitial begin\n'
    expected = []
    for i, (a,b) in enumerate(product(VALUES, repeat=2)):
        code += f"a=1'b{a};b=1'b{b};#10;$display(\"TRACE i={i} q=%b\",q);\n"
        bits = [evaluate(kind,a,b), evaluate(kind,b,b), evaluate(kind,invert(a),b)]
        expected.append(f'TRACE i={i} q=' + ''.join(reversed(bits)))
    return code + '$finish;end endmodule\n', expected
