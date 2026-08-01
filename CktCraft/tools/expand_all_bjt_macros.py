import re
import sys

def find_matching_paren(s, start):
    depth = 0
    for i in range(start, len(s)):
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return -1

def split_args(args_str):
    """Split arguments by comma, handling nested parens and strings."""
    args = []
    depth = 0
    in_string = False
    current = []
    for c in args_str:
        if c == '"' and not in_string:
            in_string = True
            current.append(c)
        elif c == '"' and in_string:
            in_string = False
            current.append(c)
        elif c == '(' and not in_string:
            depth += 1
            current.append(c)
        elif c == ')' and not in_string:
            depth -= 1
            current.append(c)
        elif c == ',' and depth == 0 and not in_string:
            args.append(''.join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        args.append(''.join(current).strip())
    return args

def expand_macro_calls(content, macro_defs):
    """Expand all macro calls using the provided definitions."""
    for name, (params, body) in macro_defs.items():
        search = '`' + name + '('
        result = []
        pos = 0
        while True:
            idx = content.find(search, pos)
            if idx == -1:
                result.append(content[pos:])
                break
            close = find_matching_paren(content, idx + len(name) + 1)
            if close == -1:
                result.append(content[pos:])
                break
            args_str = content[idx + len(name) + 2 : close]
            args = split_args(args_str)
            expanded = body
            if len(args) >= len(params):
                for pi, param in enumerate(params):
                    expanded = re.sub(r'\b' + re.escape(param) + r'\b', args[pi], expanded)
            result.append(content[pos:idx])
            result.append(expanded)
            pos = close + 1
        content = ''.join(result)
    return content

def parse_macro_definitions(content):
    """Parse ALL function-like macro definitions and remove them."""
    macros = {}
    lines = content.split('\n')
    output_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'`define\s+(\w+)\(([^)]*)\)\s*(.*)', line)
        if m:
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(',') if p.strip()]
            body = m.group(3).rstrip()
            while body.endswith('\\') and i + 1 < len(lines):
                i += 1
                body = body[:-1].rstrip() + ' ' + lines[i].strip()
            body = re.sub(r'\(\*[^*]*\*\)', '', body).strip()
            macros[name] = (params, body)
            i += 1
            continue
        output_lines.append(line)
        i += 1
    return '\n'.join(output_lines), macros

with open(sys.argv[1], 'r') as f:
    content = f.read()

# Parse and remove function-like macro definitions
content, macros = parse_macro_definitions(content)
print(f"Parsed {len(macros)} function-like macros: {list(macros.keys())}")

# Expand all macro calls
content = expand_macro_calls(content, macros)

# Check for remaining backtick macro calls
remaining = re.findall(r'`\w+\(', content)
if remaining:
    print(f"WARNING: {len(remaining)} unexpanded macro calls remain")
    # Show unique ones
    unique = set(remaining)
    for u in sorted(unique):
        print(f"  {u}")

with open(sys.argv[2], 'w') as f:
    f.write(content)
print(f"Output: {len(content.splitlines())} lines")
