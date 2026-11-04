"""Check the entire one-partition generated model, excluding its CLI adapter."""

def ordinary_cpp(code):
    begin='// Single partition argument adapter.\n'
    end='// End single partition argument adapter.\n'
    assert code.count(begin)==code.count(end)==1
    start=code.index(begin);stop=code.index(end,start)+len(end)
    code=code[:start]+code[stop:]
    lines=code.splitlines(keepends=True)
    chosen=[line for line in lines if line.endswith('// Single partition statistics.\n')]
    assert len(chosen)==1
    return ''.join(line for line in lines if line!=chosen[0])
