"""Comprehensive rebuild: converter → dedup → Wire→Reg → PCGen fix."""
import re, glob, sys, os
sys.path.insert(0, '.')

# Step 1: Run converter
os.system(f'{sys.executable} _build_dsl.py 2>/dev/null')
print('Step 1: Converter done')

# Step 2: Deduplicate
for fpath in sorted(glob.glob('skills/cpu/layer3_dsl/*.py')):
    with open(fpath) as f:
        content = f.read()
    classes = list(re.finditer(r'^class (\w+)\(Module\):', content, re.MULTILINE))
    if not classes:
        continue
    class_info = []
    for i, m in enumerate(classes):
        start = m.start()
        end = classes[i+1].start() if i+1 < len(classes) else len(content)
        class_info.append((m.group(1), start, end))
    seen = {}; to_remove = []
    for name, start, end in class_info:
        if name in seen:
            prev_start, prev_end = seen[name]
            if (end - start) > (prev_end - prev_start):
                to_remove.append((prev_start, prev_end))
                seen[name] = (start, end)
            else:
                to_remove.append((start, end))
        else:
            seen[name] = (start, end)
    to_remove.sort(reverse=True)
    for start, end in to_remove:
        content = content[:start] + content[end:]
    with open(fpath, 'w') as f:
        f.write(content)
print('Step 2: Dedup done')

# Step 3: Wire→Reg fix
for fpath in sorted(glob.glob('skills/cpu/layer3_dsl/*.py')):
    with open(fpath) as f:
        content = f.read()
    seq_blocks = list(re.finditer(r'@self\.seq\(.*?\)\s*\n\s*def _seq\(\):(.*?)(?=\n\s*@|\n\s*class|\Z)', content, re.DOTALL))
    if not seq_blocks:
        continue
    seq_assigned = set()
    for m in seq_blocks:
        for n in re.findall(r'self\.(\w+)\s*<<=', m.group(1)):
            seq_assigned.add(n)
    changes = 0
    for name in seq_assigned:
        old = f'self.{name} = Wire('
        new = f'self.{name} = Reg('
        if old in content:
            content = content.replace(old, new)
            changes += 1
    if changes:
        with open(fpath, 'w') as f:
            f.write(content)
print('Step 3: Wire→Reg done')

# Step 4: Add PCGen submodule wires
content = open('skills/cpu/layer3_dsl/pcgen.py').read()
old = 'self.u_pcreg_next_pc = Wire(39, "u_pcreg_next_pc")'
new = old + '\n' + '\n'.join(
    f'self.{w} = Wire({width}, "{w}")'
    for w, width in [('u_rmux_target', 39), ('u_rmux_any_vld', 1), ('u_l0_hit', 1), ('u_l0_target', 39), ('u_wp_way', 2), ('u_pcreg_pc', 39)]
)
if old in content:
    content = content.replace(old, new)
    with open('skills/cpu/layer3_dsl/pcgen.py', 'w') as f:
        f.write(content)
print('Step 4: PCGen wires done')

# Verify imports
ok = 0; err = []
for fpath in sorted(glob.glob('skills/cpu/layer3_dsl/*.py')):
    name = fpath.split('/')[-1][:-3]
    if name == '__init__':
        continue
    try:
        spec = importlib.util.spec_from_file_location(name, fpath)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        classes = [x for x in dir(m) if isinstance(getattr(m, x), type) and 'Module' in str(type(getattr(m, x)))]
        if classes:
            ok += 1
        else:
            err.append((name, 'no Module classes'))
    except Exception as e:
        err.append((name, str(e)[:100]))
print(f'Step 5: {ok} files import OK, {len(err)} errors')
for n, e in err:
    print(f'  {n}: {e}')
