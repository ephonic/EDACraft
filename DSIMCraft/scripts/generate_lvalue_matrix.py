#!/usr/bin/env python3
"""Generate a deterministic assignment corpus and an independent bit-list oracle."""
import argparse
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[1]


def generate(style="vcs"):
    rng = random.Random(1017)
    dimensions = {'a': (8, 0), 'b': (8, 0), 'wide': (64, 0), 'shifted': (16, 8)}
    values = {name: ['0']*width for name, (width, _) in dimensions.items()}
    source = ['// Generated with seed 1017 by scripts/generate_lvalue_matrix.py.', 'module top;']
    for name, (width, low) in dimensions.items():
        source.append(f'  reg [{low+width-1}:{low}] {name};')
    source += ['  initial begin', '    a=0; b=0; wide=0; shifted=0;']
    expected = []

    def assignment():
        pieces = []
        budget = 64
        for _ in range(rng.randint(1, 4)):
            name = rng.choice(list(dimensions))
            width, low = dimensions[name]
            count = rng.randint(1, min(width, budget))
            start = rng.randint(0, width-count)
            pieces.append((name, start, count))
            budget -= count
            if not budget:
                break
        literal_width = rng.randint(1, 64)
        bits = [rng.choice('01xz') for _ in range(literal_width)]  # low bit first
        text = []
        for name, start, count in pieces:
            low = dimensions[name][1]+start
            text.append(f'{name}[{low}]' if count == 1 else f'{name}[{low+count-1}:{low}]')
        lhs = text[0] if len(text) == 1 else '{'+','.join(text)+'}'
        literal = f"{literal_width}'b{''.join(reversed(bits))}"
        # Sized unsigned constants zero-extend to the assignment context.
        captured = (bits+['0']*64)[:sum(p[2] for p in pieces)]
        return lhs, literal, pieces, captured

    def commit(operation):
        _, _, pieces, captured = operation
        if style == 'vcs':
            offset = len(captured)
            for name, start, count in pieces:
                offset -= count
                values[name][start:start+count] = captured[offset:offset+count]
        else:
            offset = 0
            for name, start, count in reversed(pieces):
                values[name][start:start+count] = captured[offset:offset+count]
                offset += count

    def observe(label, delay):
        names = list(dimensions)
        fields = ' '.join(f'{name}=%b' for name in names)
        source.append(f'    #{delay} $display("TRACE {label} {fields}",'+','.join(names)+');')
        expected.append('TRACE '+label+' '+' '.join(f"{name}={''.join(reversed(values[name]))}" for name in names))

    for phase in range(6):
        for _ in range(3):
            operation = assignment()
            source.append(f'    {operation[0]}={operation[1]};')
            commit(operation)
        pending = []
        for _ in range(4):
            operation = assignment()
            source.append(f'    {operation[0]}<={operation[1]};')
            pending.append(operation)
        operation = assignment()
        source.append(f'    {operation[0]}={operation[1]};')
        commit(operation)
        observe(f'p{phase}_inactive', 0)
        for operation in pending:
            commit(operation)
        observe(f'p{phase}_committed', 1)
    source += ['    $finish;', '  end', 'endmodule', '']
    return '\n'.join(source), json.dumps(expected, indent=2)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source, expected = generate()
    icarus_source, icarus_expected = generate('icarus')
    assert icarus_source == source
    for name, content in [('lvalue_matrix.v', source), ('lvalue_matrix.expected.json', expected),
                          ('lvalue_matrix.icarus.json', icarus_expected)]:
        path = ROOT/'tests/cases'/name
        if args.check:
            if path.read_text() != content:
                raise RuntimeError(f'Generated fixture is stale: {path}')
        else:
            path.write_text(content)
    print('PASS deterministic lvalue corpus' if args.check else 'Generated deterministic lvalue corpus')


if __name__ == '__main__':
    main()
