import re
import sys

def find_matching_paren(s, start):
    """Find the matching closing paren for the opening paren at position start."""
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1

def expand_macro_call(content, macro_name, expander):
    """Find and expand all calls to `macro_name(args) handling nested parens."""
    search = '`' + macro_name + '('
    result = []
    pos = 0
    while True:
        idx = content.find(search, pos)
        if idx == -1:
            result.append(content[pos:])
            break
        # Find matching closing paren
        close = find_matching_paren(content, idx + len(macro_name) + 1)
        if close == -1:
            result.append(content[pos:])
            break
        args_str = content[idx + len(macro_name) + 2 : close]
        expansion = expander(args_str)
        result.append(content[pos:idx])
        result.append(expansion)
        pos = close + 1
    return ''.join(result)

def expand_explin(args):
    parts = args.split(',', 1)
    if len(parts) == 2:
        return f'{parts[0].strip()} = exp({parts[1].strip()});'
    return f'`expLin({args})'

def expand_maxhyp0(args):
    parts = [p.strip() for p in args.split(',')]
    if len(parts) == 3:
        r, x, e = parts
        return f'{r} = 0.5 * (sqrt({x} * {x} + {e} * {e}) + {x});'
    return f'`max_hyp0({args})'

def expand_minlogexp(args):
    parts = [p.strip() for p in args.split(',')]
    if len(parts) == 4:
        r, x, x0, a = parts
        return f'{r} = {x} - {a} * log(1.0 + exp(({x} - {x0}) / {a}));'
    return f'`min_logexp({args})'

def expand_maxlogexp(args):
    parts = [p.strip() for p in args.split(',')]
    if len(parts) == 4:
        r, x, x0, a = parts
        return f'{r} = {x0} + {a} * log(1.0 + exp(({x} - {x0}) / {a}));'
    return f'`max_logexp({args})'

def expand_linlog(args):
    parts = [p.strip() for p in args.split(',')]
    if len(parts) == 3:
        r, x, vlim = parts
        return f'{r} = {x};'
    return f'`linLog({args})'

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Also remove multi-line macro definitions
lines = content.split('\n')
output_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    if re.match(r'`define\s+(max_hyp0|min_logexp|max_logexp|expLin|linLog)\b', line):
        while i < len(lines) and lines[i].rstrip().endswith('\\'):
            i += 1
        i += 1
        continue
    output_lines.append(line)
    i += 1
content = '\n'.join(output_lines)

# Expand macro calls with proper nested paren handling
content = expand_macro_call(content, 'expLin', expand_explin)
content = expand_macro_call(content, 'max_hyp0', expand_maxhyp0)
content = expand_macro_call(content, 'min_logexp', expand_minlogexp)
content = expand_macro_call(content, 'max_logexp', expand_maxlogexp)
content = expand_macro_call(content, 'linLog', expand_linlog)

with open(sys.argv[2], 'w') as f:
    f.write(content)
print(f'Output: {len(content.splitlines())} lines')
