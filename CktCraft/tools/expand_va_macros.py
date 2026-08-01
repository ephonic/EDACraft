#!/usr/bin/env python3
"""Expand ONLY function-like Verilog-A macros. Keep simple macros for preprocessor."""
import re
import sys

def expand_function_macros(input_file, output_file):
    with open(input_file, 'r') as f:
        lines = f.readlines()

    # Parse ONLY function-like macro definitions
    func_macros = {}
    output_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check for function-like macro: `define NAME(params) ...
        m = re.match(r'`define\s+(\w+)\(([^)]*)\)\s*(.*)', line)
        if m:
            name = m.group(1)
            params = [p.strip() for p in m.group(2).split(',') if p.strip()]
            body = m.group(3).rstrip()
            # Handle multi-line macros (lines ending with \)
            while body.endswith('\\') and i + 1 < len(lines):
                i += 1
                body = body[:-1].rstrip() + ' ' + lines[i].strip()
            # Remove (*...*) attributes from body
            body = re.sub(r'\(\*[^*]*\*\)', '', body).strip()
            func_macros[name] = (params, body)
            i += 1
            continue  # Skip the definition line
        # Keep all other lines (including simple `define)
        output_lines.append(line)
        i += 1

    # Expand function-like macro calls in remaining lines
    expanded_lines = []
    for line in output_lines:
        expanded = line
        changed = True
        while changed:
            changed = False
            for name, (params, body) in func_macros.items():
                pattern = '`' + name + '('
                idx = expanded.find(pattern)
                if idx == -1:
                    continue
                # Find matching closing paren
                depth = 0
                j = idx + len(pattern)
                while j < len(expanded):
                    if expanded[j] == '(':
                        depth += 1
                    elif expanded[j] == ')':
                        if depth == 0:
                            break
                        depth -= 1
                    j += 1
                if j >= len(expanded):
                    continue
                args_str = expanded[idx + len(pattern) : j]
                args = [a.strip() for a in args_str.split(',')]
                expanded_body = body
                if len(args) >= len(params):
                    for pi, param in enumerate(params):
                        expanded_body = re.sub(r'\b' + re.escape(param) + r'\b', args[pi], expanded_body)
                expanded = expanded[:idx] + expanded_body + expanded[j+1:]
                changed = True
        expanded_lines.append(expanded)

    with open(output_file, 'w') as f:
        f.writelines(expanded_lines)

    print(f"Expanded {len(func_macros)} function-like macros: {list(func_macros.keys())}")
    print(f"Output: {output_file} ({len(expanded_lines)} lines)")

if __name__ == '__main__':
    expand_function_macros(sys.argv[1], sys.argv[2])
