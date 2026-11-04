"""Independent decoder restores the old C++ layout for bytewise comparison."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def expand(cpp):
    header = (ROOT / 'include/dsim/path_dictionary.hpp').read_text().removeprefix('#pragma once\n')
    assert cpp.count('\n' + header) == 1
    cpp = cpp.replace('\n' + header, '', 1)
    prefix = 'static const uint64_t path_delay_tables[][12]={'
    start = cpp.index(prefix); end = cpp.index('};\n', start) + 3
    body = cpp[start + len(prefix):end - 3]
    rows = re.findall(r'\{((?:\d+ULL,){12})\},', body)
    assert re.sub(r'\{(?:\d+ULL,){12}\},', '', body) == '{0}'
    assert len(set(rows)) == len(rows), 'dictionary contains duplicate delays'
    cpp = cpp[:start] + cpp[end:]
    conditional = 'static const DictionaryConditionalModulePathArc path_arcs[]={' in cpp
    kind = 'DictionaryConditionalModulePathArc' if conditional else 'DictionaryModulePathArc'
    prefix = 'static const ' + kind + ' path_arcs[]={'
    start = cpp.index(prefix); end = cpp.index('};\n', start) + 3
    body = cpp[start + len(prefix):end - 3]
    if conditional:
        pattern = r'\{\{(\d+),(\d+),(\d+)\},(\d+),(\d+),(true|false)\},'
        entries = re.findall(pattern, body)
        assert re.sub(pattern, '', body) == '{{0,0,0},0,0,false}'
        reconstructed = 'static const ConditionalModulePathArc path_arcs[]={'
        for pin, index, edge, first, condition, fallback in entries:
            assert int(index) < len(rows)
            reconstructed += '{{' + pin + ',' + edge + ',{' + rows[int(index)] + '}},' + first + ',' + condition + ',' + fallback + '},'
        reconstructed += '{{0,0,{}},0,0,false}};\n'
    else:
        pattern = r'\{(\d+),(\d+),(\d+)\},'
        entries = re.findall(pattern, body)
        assert re.sub(pattern, '', body) == '{0,0,0}'
        reconstructed = 'static const ModulePathArc path_arcs[]={'
        for pin, index, edge in entries:
            assert int(index) < len(rows)
            reconstructed += '{' + pin + ',' + edge + ',{' + rows[int(index)] + '}},'
        reconstructed += '{0,0,{}}};\n'
    cpp = cpp[:start] + reconstructed + cpp[end:]
    cpp = cpp.replace('dictionary_conditional_module_path_delay(', 'conditional_module_path_delay(')
    cpp = cpp.replace('dictionary_module_path_delay(', 'module_path_delay(')
    assert cpp.count(',path_delay_tables)') == 1
    cpp = cpp.replace(',path_delay_tables)', ')', 1)
    return cpp, dict(arcs=len(entries), distinct_tables=len(rows), conditional=conditional,
                    baseline_table_bytes=len(entries) * (120 if conditional else 104),
                    dictionary_table_bytes=len(entries) * (24 if conditional else 12) + len(rows) * 96)
