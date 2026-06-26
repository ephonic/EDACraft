#!/usr/bin/env python3
"""
Rebuild all CPU layer3_dsl module files from Verilog sources.
"""
import os, re, sys, glob
from typing import List, Tuple, Optional, Dict, Set

INDENT = "    "

def convert_literals(expr: str) -> str:
    def _conv(m):
        lit = m.group(0)
        m2 = re.match(r"(\d+)'([bdoh])([\da-fA-FxXzZ_]+)", lit)
        if not m2:
            return lit
        width = int(m2.group(1))
        base = m2.group(2)
        val_str = m2.group(3).replace("_", "")
        try:
            if base == 'd': return val_str
            elif base == 'h': return str(int(val_str, 16))
            elif base == 'o': return str(int(val_str, 8))
            elif base == 'b': return str(int(val_str, 2))
        except: pass
        return lit
    return re.sub(r"\d+'[bdoh][\da-fA-FxXzZ_]+", _conv, expr)

SELF_SIGS: Set[str] = set()

def add_self(expr: str) -> str:
    """Add self. prefix to unqualified identifiers."""
    if not expr:
        return expr
    result = []
    i = 0
    while i < len(expr):
        if expr[i] == '.' and i > 0:
            # DOT-ACCESSED - copy the whole thing
            j = i + 1
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            result.append(expr[i:j])
            i = j
            continue
        if expr[i].isalpha() or expr[i] == '_':
            j = i + 1
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            ident = expr[i:j]
            if ident in SELF_SIGS:
                result.append(f'self.{ident}')
            elif not ident[0].isupper() and ident not in (
                'if', 'else', 'begin', 'end', 'case', 'default', 'for', 'while',
                'posedge', 'negedge', 'input', 'output', 'reg', 'wire', 'logic',
                'module', 'endmodule', 'always', 'assign',
            ):
                result.append(f'self.{ident}')
            else:
                result.append(ident)
            i = j
        else:
            result.append(expr[i])
            i += 1
    return ''.join(result)


def parse_verilog_module(text: str) -> Optional[dict]:
    """Parse a Verilog module definition and return structured data."""
    m = re.search(r'module\s+(\w+)\s*\(', text)
    if not m:
        return None
    mod_name = m.group(1)
    
    result = {
        'name': mod_name,
        'ports': [],
        'wires': [],
        'regs': [],
        'arrays': [],
        'comb_body': '',
        'seq_body': '',
    }
    
    # === Extract ports ===
    # The '(' was consumed by the regex, so paren_depth starts at 1
    paren_depth = 1
    start = m.end()  # points right after '('
    ports_text = ""
    for i in range(start, len(text)):
        if text[i] == '(':
            paren_depth += 1
        elif text[i] == ')':
            paren_depth -= 1
            if paren_depth == 0:
                ports_text = text[start:i]
                break
    
    if ports_text:
        # Parse each port (separated by commas, may span multiple lines)
        port_lines_raw = ports_text.split(',')
        for pline in port_lines_raw:
            p = _parse_port(pline)
            if p:
                result['ports'].append(p)
    
    # === Extract internals ===
    body = ''
    endm = text.find('endmodule', m.start())
    if endm > 0:
        # Find the ); closing the port list
        # The matching ')' was found at position 'i' in the loop above
        # Let's find ); after the opening
        close_semi = text.find(');', m.start())
        if close_semi >= 0:
            body = text[close_semi+2:endm]
        else:
            body = text[m.end():endm]  # fallback
    
    # Process declarations line by line
    for line in body.split(';'):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('always') or line.startswith('end'):
            continue
        
        # Array: reg/logic [W:0] name [0:D]
        am = re.match(r'(reg|logic|wire)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s+(\w+)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]', line)
        if am:
            kw = am.group(1)
            msb, lsb = am.group(2), am.group(3)
            name = am.group(4)
            amsb, alsb = am.group(5), am.group(6)
            width = int(msb) - int(lsb) + 1 if msb and lsb else 1
            depth = abs(int(amsb) - int(alsb)) + 1
            result['arrays'].append({'name': name, 'width': width, 'depth': depth})
            continue
        
        # Scalar/vector: reg/logic [W:0] name (no array)
        dm = re.match(r'(reg|logic|wire)\s*(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s+(\w+)', line)
        if dm:
            kw = dm.group(1)
            msb, lsb = dm.group(2), dm.group(3)
            name = dm.group(4)
            width = int(msb) - int(lsb) + 1 if msb and lsb else 1
            entry = {'name': name, 'width': width}
            if kw == 'reg':
                result['regs'].append(entry)
            else:
                result['wires'].append(entry)
            continue
    
    # === Extract combinational always block ===
    idx = text.find('always @(*)')
    if idx >= 0:
        body_text = _extract_always_body(text, idx)
        if body_text:
            result['comb_body'] = body_text
    
    # === Extract sequential always block ===
    sm = re.search(r'always\s+@\(posedge\s+(\w+)\s+or\s+negedge\s+(\w+)\)', text)
    if sm:
        body_text = _extract_always_body(text, sm.start())
        if body_text:
            result['seq_body'] = body_text
    
    return result


def _parse_port(line: str) -> Optional[dict]:
    """Parse a single port declaration (without leading/trailing spaces)."""
    line = re.sub(r'\s+', ' ', line).strip()
    # Remove trailing comma
    line = line.rstrip(',').strip()
    if not line:
        return None
    
    # input/output [reg] [wire] [logic] [[W:0]] name
    m = re.match(
        r'(input|output)\s+(reg\s+)?(wire\s+)?(logic\s+)?'
        r'(?:\[\s*(\d+)\s*:\s*(\d+)\s*\])?\s*'
        r'(\w[\w\[\]]*)',
        line
    )
    if m:
        direction = m.group(1)
        msb, lsb = m.group(5), m.group(6)
        name = m.group(7).strip().rstrip(',')
        if msb and lsb:
            width = int(msb) - int(lsb) + 1
        else:
            width = 1
        return {'name': name, 'direction': direction, 'width': width}
    return None


def _extract_always_body(text: str, start_idx: int) -> str:
    """Extract the body between begin..end of an always block starting at start_idx."""
    # Find the first 'begin' after start_idx as a whole word
    bi = _find_word(text, 'begin', start_idx)
    if bi < 0:
        return ''
    body_start = bi + 5
    depth = 1
    i = body_start
    while i < len(text) and depth > 0:
        if _is_word_at(text, i, 'begin'):
            depth += 1
            i += 5
        elif _is_word_at(text, i, 'end'):
            depth -= 1
            i += 3
        else:
            i += 1
    if depth == 0:
        return text[body_start:i-3].strip()
    return text[body_start:].strip()

def _find_word(text: str, word: str, start: int = 0) -> int:
    """Find a whole word in text starting from position start."""
    while True:
        pos = text.find(word, start)
        if pos < 0:
            return -1
        if _is_word_at(text, pos, word):
            return pos
        start = pos + 1

def _is_word_at(text: str, pos: int, word: str) -> bool:
    """Check if word appears at position pos as a whole word."""
    if text[pos:pos+len(word)] != word:
        return False
    after = pos + len(word)
    # Check that it's not mid-word: char before should be non-alphanumeric or start
    if pos > 0 and (text[pos-1].isalnum() or text[pos-1] == '_'):
        return False
    # Check char after
    if after < len(text) and (text[after].isalnum() or text[after] == '_'):
        return False
    return True


def _parenthesize_comparisons(expr: str) -> str:
    """Add parentheses around comparison sub-expressions when mixed with & or |.
    
    Verilog: a == 1 & b == 2  →  (a == 1) & (b == 2)
    Python: a == 1 & b == 2 is WRONG (parsed as a == (1 & b) == 2)
    """
    # Strategy: find all comparison ops (==, !=, <, >, <=, >=) that have & or | nearby
    # and wrap them in parens.
    # We scan for pattern: <expr> <op> <expr> where <op> is a comparison,
    # and if there's a & or | anywhere, wrap.
    import re
    # Wrap each comparison in parens if not already wrapped
    # Pattern: word/expr comparison_op word/expr
    # Simple approach: replace all comparisons with parenthesized versions
    result = re.sub(
        r'(\w[\w\[\]:]*)\s*(==|!=|<=|>=|<|>)\s*(\w[\w\[\]:]*)',
        r'(\1 \2 \3)',
        expr
    )
    return result

def _clean_condition(expr: str) -> str:
    """Clean a Verilog condition: convert literals, add self. prefix, fix precedence."""
    expr = convert_literals(expr)
    expr = _parenthesize_comparisons(expr)
    expr = add_self(expr)
    return expr

def _convert_concat_rhs(rhs: str) -> str:
    """Convert Verilog concatenation/replication to Cat/Rep calls.
    
    {{52{self.instr[31]}}, self.instr[31:20]} 
    → Cat(Rep(self.instr[31], 52), self.instr[31:20])
    
    {0, self.instr[31:12], 0}
    → Cat(0, self.instr[31:12], 0)
    """
    # Only process if there's a top-level {...}
    if not rhs.strip().startswith('{'):
        return rhs
    
    # Find matching closing brace at top level
    depth = 0
    end = -1
    for i, ch in enumerate(rhs):
        if ch == '{':
            depth += 1
            if depth == 1:
                start = i
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    
    if end < 0:
        return rhs
    
    inner = rhs[start+1:end].strip()
    
    # Parse inner contents into items, handling nested braces
    items = []
    depth = 0
    current = ''
    for ch in inner:
        if ch == '{':
            depth += 1
            current += ch
        elif ch == '}':
            depth -= 1
            current += ch
        elif ch == ',' and depth == 0:
            items.append(current.strip())
            current = ''
        else:
            current += ch
    if current.strip():
        items.append(current.strip())
    
    # Convert each item
    converted_items = []
    for item in items:
        item = item.strip()
        # Check for replication: {N{expr}} 
        rep_m = re.match(r'\{(\d+)\{(.+)\}\}', item)
        if rep_m:
            n = rep_m.group(1)
            inner_expr = rep_m.group(2)
            converted_items.append(f'Rep({inner_expr}, {n})')
        else:
            # Also check for bare N{expr} (without outer braces)
            rep_m2 = re.match(r'(\d+)\{(.+)\}', item)
            if rep_m2:
                n = rep_m2.group(1)
                inner_expr = rep_m2.group(2)
                converted_items.append(f'Rep({inner_expr}, {n})')
            else:
                converted_items.append(item)
    
    return f'Cat({", ".join(converted_items)})'

def convert_always_body(body: str) -> List[str]:
    """Convert Verilog always block body to DSL statements with proper indentation."""
    result = []
    # Process line by line
    lines = body.split('\n')
    
    # First pass: clean and standardize
    clean_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('//'):
            continue
        clean_lines.append(line)
    
    body_clean = ' '.join(clean_lines)
    # Normalize
    body_clean = re.sub(r'\s+', ' ', body_clean)
    
    # Token-based parsing for if/else/assignments
    tokens = _tokenize_body(body_clean)
    
    # Merge 'else if' -> 'elif' after 'end' handling
    merged = []
    i = 0
    while i < len(tokens):
        if i + 2 < len(tokens) and tokens[i][0] == 'end' and tokens[i+1][0] == 'else' and tokens[i+2][0] == 'if' and tokens[i+2][1] != '':
            # Keep end, then merge else+if -> elif
            merged.append(('end', ''))
            merged.append(('elif', tokens[i+2][1]))
            i += 3
        elif i + 1 < len(tokens) and tokens[i][0] == 'end' and tokens[i+1][0] == 'else':
            # Keep end, then keep else
            merged.append(('end', ''))
            merged.append(('else', ''))
            i += 2
        # Note: standalone 'if' after 'end' is a NEW if, not related to previous
        else:
            merged.append(tokens[i])
            i += 1
    
    depth = 0
    lines_out = []
    
    for tok_type, tok_val in merged:
        if tok_type == 'begin':
            depth += 1
        elif tok_type == 'end':
            depth = max(0, depth - 1)
        elif tok_type == 'if':
            cond = _clean_condition(tok_val)
            lines_out.append(f'{INDENT * depth}with If({cond}):')
        elif tok_type == 'elif':
            cond = _clean_condition(tok_val)
            lines_out.append(f'{INDENT * depth}with Elif({cond}):')
        elif tok_type == 'else':
            lines_out.append(f'{INDENT * depth}with Else():')
        elif tok_type == 'assign':
            a = _convert_assign(tok_val)
            if a:
                lines_out.append(f'{INDENT * depth}{a}')
        elif tok_type == 'raw':
            lines_out.append(f'{INDENT * depth}# {tok_val}')
    
    # Post-process: add pass to empty blocks
    # If a 'with If/Elif/Else(...):' line is followed by another
    # 'with If/Elif/Else' at the same indent, insert 'pass'
    result = []
    for i, line in enumerate(lines_out):
        result.append(line)
        # Check if this is a with If/Elif/Else line
        if re.match(r'^\s*with (If|Elif|Else)\(', line):
            # Check the next non-blank line at the same or lower indent
            next_line = ''
            for j in range(i+1, len(lines_out)):
                if lines_out[j].strip():
                    next_line = lines_out[j]
                    break
            if next_line:
                curr_indent = len(line) - len(line.lstrip())
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= curr_indent:
                    # Empty block - add 'pass'
                    result.append(f'{INDENT * (curr_indent // 4 + 1)}pass')
    
    return result


def _tokenize_body(body: str) -> List[Tuple[str, str]]:
    """Tokenize Verilog body into if/elif/else/begin/end/assign tokens."""
    tokens = []
    i = 0
    while i < len(body):
        # Skip whitespace
        if body[i] in ' \t\n\r':
            i += 1
            continue
        
        # Skip comments
        if body[i:i+2] == '//':
            nl = body.find('\n', i)
            i = nl + 1 if nl >= 0 else len(body)
            continue
        
        # end
        if body[i:i+3] == 'end':
            tokens.append(('end', ''))
            i += 3
            continue
        
        # begin
        if body[i:i+5] == 'begin':
            tokens.append(('begin', ''))
            i += 5
            continue
        
        # else if
        if body[i:i+8] == 'else if':
            # Find the condition in parentheses
            ci = body.find('(', i+8)
            if ci >= 0:
                depth = 0
                j = ci
                while j < len(body):
                    if body[j] == '(':
                        depth += 1
                    elif body[j] == ')':
                        depth -= 1
                        if depth == 0:
                            cond = body[ci+1:j].strip()
                            tokens.append(('elif', cond))
                            i = j + 1
                            break
                    j += 1
                else:
                    i += 8
            else:
                i += 8
            continue
        
        # else
        if body[i:i+4] == 'else' and (i+4 >= len(body) or body[i+4] in ' \t\n\r({;'):
            tokens.append(('else', ''))
            i += 4
            continue
        
        # if
        if body[i:i+2] == 'if' and (i+2 >= len(body) or body[i+2] in ' \t\n\r('):
            # Find condition in parentheses
            ci = body.find('(', i+2)
            if ci >= 0:
                depth = 0
                j = ci
                while j < len(body):
                    if body[j] == '(':
                        depth += 1
                    elif body[j] == ')':
                        depth -= 1
                        if depth == 0:
                            cond = body[ci+1:j].strip()
                            tokens.append(('if', cond))
                            i = j + 1
                            break
                    j += 1
                else:
                    i += 2
            else:
                i += 2
            continue
        
        # Look for semicolon-terminated statements
        semi = body.find(';', i)
        if semi >= 0:
            stmt = body[i:semi].strip()
            if stmt:
                tokens.append(('assign', stmt))
            i = semi + 1
        else:
            # End of text
            rest = body[i:].strip()
            if rest:
                tokens.append(('raw', rest))
            break
    
    return tokens


def _convert_assign(assign_text: str) -> Optional[str]:
    """Convert a Verilog assignment to DSL <<=."""
    assign_text = assign_text.strip()
    if not assign_text:
        return None
    
    # Handle <= or = assignment
    m = re.match(r'(.+?)\s*(<=|(?<![!<>=])=(?!=))\s*(.+)', assign_text)
    if not m:
        return None
    
    lhs = m.group(1).strip()
    op = m.group(2)
    rhs = m.group(3).strip()
    
    # Clean up literals
    lhs = convert_literals(lhs)
    rhs = convert_literals(rhs)
    
    # Convert Verilog concatenation/replication
    if rhs:
        rhs = _convert_concat_rhs(rhs)
        rhs = _parenthesize_comparisons(rhs)
    
    # Add self. prefix
    lhs = add_self(lhs)
    rhs = add_self(rhs) if rhs else rhs
    
    if not rhs:
        return None
    
    return f'{lhs} <<= {rhs}'


# =====================================================================
# Module-to-file mapping
# =====================================================================
NAME_TO_FILE = {
    "ALU": "alu", "IBuf": "ibuf", "IBuf_spec": "ibuf_spec",
    "BPred": "bpred", "PCGen": "pcgen",
    "PCGen_C910": "pcgen", "PCGen_Simpl": "pcgen",
    "PCReg": "pcgen", "L0BTB": "pcgen", "RedirectMux": "pcgen", "WayPred": "pcgen",
    "AddrGen": "ifu_common", "ICacheIF": "ifu_common", "IFCtrl": "ifu_common", "LBuf": "ifu_common",
    "IndirectBranchBTB": "ifu_ind_btb", "PreDecodeBuffer": "ifu_predecode",
    "PCFifo": "ifu_pcfifo", "VectorFetch": "ifu_vector", "L1Refill": "ifu_l1_refill",
    "SFP": "ifu_sfp", "IFUDebug": "ifu_debug",
    "Decoder": "idu_decode", "IRCtrl": "idu_ir_ctrl", "ISCtrl": "idu_is_ctrl",
    "SDIQ": "idu_issue_extra", "VIQ": "idu_issue_extra",
    "RFWriteCtrl": "idu_rf_ctrl", "RFReadCtrl": "idu_rf_ctrl",
    "PRF": "idu_rf_pregfile", "FwdNet": "idu_rf_fwd", "FenceUnit": "idu_fence",
    "FRenameTable": "idu_ir_frt", "VRenameTable": "idu_ir_vrt",
    "RenameTable": "rename", "IssueQueue": "issue_queue",
    "BJU": "iu_bju", "ResultBus": "iu_cbus", "Divider": "iu_div",
    "Multiplier": "iu_mult", "SpecialUnit": "iu_special", "MulDiv": "muldiv",
    "LSU": "lsu", "LSAddrGen": "lsu_addrgen", "AtomicOp": "lsu_amr",
    "BusArb": "lsu_bus_arb", "CacheBuffer": "lsu_cache_buffer",
    "LSUCtrl": "lsu_ctrl", "DCacheIF": "lsu_dcache", "DCacheTop": "lsu_dcache_top",
    "ICC": "lsu_icc", "LoadAddrGen": "lsu_ld_ag", "LoadDataArray": "lsu_ld_da",
    "LSDataCheck": "lsu_ld_st_dc", "LFB": "lsu_lfb", "LoadMiss": "lsu_lm",
    "MCIC": "lsu_mcic", "PrefetchUnit": "lsu_pfu",
    "LoadQueue": "lsu_queue", "StoreQueue": "lsu_queue",
    "LSReorderBuf": "lsu_rb", "StoreDataExt": "lsu_sd_ex1",
    "SnoopCtrl": "lsu_snoop", "SnoopCtrlTQ": "lsu_snoop_ctcq",
    "SnoopReqArb": "lsu_snoop_req_arb", "SnoopResp": "lsu_snoop_resp",
    "SnoopSNQ": "lsu_snoop_snq", "SpecFailPredict": "lsu_spec_fail_predict",
    "StoreAddrGen": "lsu_st_ag", "StoreDataArray": "lsu_st_da",
    "VictimBuffer": "lsu_vb", "VBStoreData": "lsu_vb_sdb",
    "LoadWriteback": "lsu_wb", "StoreWriteback": "lsu_wb", "WMB": "lsu_wmb",
    "ROB": "rob", "CommitUnit": "rtu_commit", "PST": "rtu_pst",
    "PSTExtra": "rtu_pst_extra", "RetireUnit": "rtu_retire",
    "ITLB": "mmu_tlb", "DTLB": "mmu_tlb", "L2TLB": "mmu_l2tlb",
    "PTW": "mmu_ptw", "MMU": "mmu_top", "CSRFile": "csr",
    "TageTable": "tage", "StatisticalCorrector": "tage", "TageSC": "tage",
    "ReservationStation": "ooo_issue", "DispatchUnit": "ooo_issue", "OoOCore": "ooo_issue",
    "Trap": "trap", "C910Pipeline": "pipeline", "ExecuteStage": "pipeline",
    "FetchStage": "fetch_stage",
}

def gen_dsl_for_module(v_path: str) -> Optional[str]:
    """Generate DSL source for one Verilog module file."""
    with open(v_path) as f:
        text = f.read()
    
    mod = parse_verilog_module(text)
    if not mod:
        return None
    
    name = mod['name']
    
    # Build list of all signal names for self. prefix replacement
    global SELF_SIGS
    SELF_SIGS = set()
    for p in mod['ports']:
        SELF_SIGS.add(p['name'])
    for w in mod['wires']:
        SELF_SIGS.add(w['name'])
    for r in mod['regs']:
        SELF_SIGS.add(r['name'])
    for a in mod['arrays']:
        SELF_SIGS.add(a['name'])
    
    # Also find implicit signals from submodule connections
    for sm in mod.get('submods', []):
        for port_name, conn_expr in sm['ports'].items():
            if conn_expr not in SELF_SIGS and conn_expr.isalnum() or '_' in conn_expr:
                SELF_SIGS.add(conn_expr)
    
    code = []
    # Ports section
    for p in mod['ports']:
        w = p['width']
        dt = p['direction'].title()
        if w == 1:
            code.append(f'{INDENT*2}self.{p["name"]} = {dt}(1, "{p["name"]}")')
        else:
            code.append(f'{INDENT*2}self.{p["name"]} = {dt}({w}, "{p["name"]}")')
    if mod['ports']:
        code.append('')
    
    for w in mod['wires']:
        if w['width'] == 1:
            code.append(f'{INDENT*2}self.{w["name"]} = Wire(1, "{w["name"]}")')
        else:
            code.append(f'{INDENT*2}self.{w["name"]} = Wire({w["width"]}, "{w["name"]}")')
    if mod['wires']:
        code.append('')
    
    for r in mod['regs']:
        if r['width'] == 1:
            code.append(f'{INDENT*2}self.{r["name"]} = Reg(1, "{r["name"]}")')
        else:
            code.append(f'{INDENT*2}self.{r["name"]} = Reg({r["width"]}, "{r["name"]}")')
    if mod['regs']:
        code.append('')
    
    for a in mod['arrays']:
        code.append(f'{INDENT*2}self.{a["name"]} = Array({a["width"]}, {a["depth"]}, "{a["name"]}")')
    if mod['arrays']:
        code.append('')
    
    # Combinational
    if mod['comb_body']:
        code.append(f'{INDENT*2}@self.comb')
        code.append(f'{INDENT*2}def _comb():')
        stmts = convert_always_body(mod['comb_body'])
        for s in stmts:
            code.append(f'{INDENT*3}{s}')
        code.append('')
    
    # Sequential
    if mod['seq_body']:
        code.append(f'{INDENT*2}@self.seq(self.clk, self.rst_n)')
        code.append(f'{INDENT*2}def _seq():')
        stmts = convert_always_body(mod['seq_body'])
        for s in stmts:
            code.append(f'{INDENT*3}{s}')
        code.append('')
    
    class_lines = [
        f'class {name}(Module):',
        f'{INDENT}def __init__(self):',
        f'{INDENT*2}super().__init__("{name.lower()}")',
        '',
    ]
    class_lines.extend(code)
    return '\n'.join(class_lines)


def main():
    src_dir = "generated_skill_ppa/cpu/hand_generated"
    target_dir = "skills/cpu/layer3_dsl"
    
    os.makedirs(target_dir, exist_ok=True)
    
    v_files = sorted(glob.glob(os.path.join(src_dir, "*.v")))
    
    # Group by output file
    file_modules = {}
    for vf in v_files:
        with open(vf) as f:
            text = f.read()
        for m in re.finditer(r'module\s+(\w+)', text):
            mod_name = m.group(1)
            fname = NAME_TO_FILE.get(mod_name, mod_name.lower())
            file_modules.setdefault(fname, []).append((mod_name, vf))
    
    built = 0
    for fname, modules in sorted(file_modules.items()):
        out_path = os.path.join(target_dir, f"{fname}.py")
        
        dsl_parts = []
        for mod_name, v_path in modules:
            dsl = gen_dsl_for_module(v_path)
            if dsl:
                dsl_parts.append(dsl)
        
        if not dsl_parts:
            continue
        
        all_code = [
            f'"""',
            f'L3 DSL — {", ".join(m for m,_ in modules)}.',
            f'"""',
            f'from rtlgen.core import Module, Input, Output, Wire, Reg, Array, Const',
            f'from rtlgen.logic import If, Else, Elif',
            '',
            '',
        ]
        all_code.append('\n\n'.join(dsl_parts))
        
        combined = '\n'.join(all_code)
        with open(out_path, 'w') as f:
            f.write(combined)
        built += 1
        lc = len(combined.splitlines())
        print(f'  {fname}.py: {lc} lines')
    
    print(f'\nBuilt {built} files')


if __name__ == '__main__':
    main()
