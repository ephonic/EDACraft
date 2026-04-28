"""
rtlgen.liberty — Liberty (.lib) parser and data model.

Supports:
- table_lookup delay model with 2D NLDM tables
- cell / pin / timing arc extraction
- drive-strength grouping for gate sizing
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class LibertyTable:
    name: str
    index_1: List[float] = field(default_factory=list)
    index_2: List[float] = field(default_factory=list)
    values: List[List[float]] = field(default_factory=list)

    def lookup(self, x: float, y: float) -> float:
        """Bilinear interpolation (clamped at boundaries)."""
        idx_1 = self.index_1
        idx_2 = self.index_2
        vals = self.values
        if not idx_1 or not idx_2 or not vals:
            return 0.0

        # Clamp
        x = max(idx_1[0], min(x, idx_1[-1]))
        y = max(idx_2[0], min(y, idx_2[-1]))

        # Find interval in index_1
        i = 0
        while i < len(idx_1) - 1 and x > idx_1[i + 1]:
            i += 1
        # Find interval in index_2
        j = 0
        while j < len(idx_2) - 1 and y > idx_2[j + 1]:
            j += 1

        x0, x1 = idx_1[i], idx_1[min(i + 1, len(idx_1) - 1)]
        y0, y1 = idx_2[j], idx_2[min(j + 1, len(idx_2) - 1)]
        dx = x1 - x0 if x1 != x0 else 1.0
        dy = y1 - y0 if y1 != y0 else 1.0
        fx = (x - x0) / dx
        fy = (y - y0) / dy

        v00 = vals[i][j]
        v01 = vals[i][min(j + 1, len(idx_2) - 1)]
        v10 = vals[min(i + 1, len(idx_1) - 1)][j]
        v11 = vals[min(i + 1, len(idx_1) - 1)][min(j + 1, len(idx_2) - 1)]

        return (
            v00 * (1 - fx) * (1 - fy)
            + v01 * (1 - fx) * fy
            + v10 * fx * (1 - fy)
            + v11 * fx * fy
        )


@dataclass
class LibertyTiming:
    related_pin: str = ""
    timing_sense: str = ""
    timing_type: str = ""
    cell_rise: Optional[LibertyTable] = None
    cell_fall: Optional[LibertyTable] = None
    rise_transition: Optional[LibertyTable] = None
    fall_transition: Optional[LibertyTable] = None


@dataclass
class LibertyPin:
    name: str
    direction: str = ""
    capacitance: float = 0.0
    max_capacitance: Optional[float] = None
    timings: List[LibertyTiming] = field(default_factory=list)
    function: Optional[str] = None


@dataclass
class LibertyCell:
    name: str
    area: float = 0.0
    leakage_power: float = 0.0
    pins: Dict[str, LibertyPin] = field(default_factory=dict)


@dataclass
class LibertyLibrary:
    name: str
    time_unit: str = "1ns"
    capacitive_load_unit: Tuple[float, str] = (1.0, "pf")
    cells: Dict[str, LibertyCell] = field(default_factory=dict)

    def cell_groups_by_function(self) -> Dict[str, List[str]]:
        """Group cells by output pin function string for gate sizing."""
        groups: Dict[str, List[str]] = {}
        for cname, cell in self.cells.items():
            func_key = None
            for pin in cell.pins.values():
                if pin.direction == "output" and pin.timings:
                    # Use function as key if available; otherwise fall back to cell name
                    func_key = f"{cname}:{pin.name}"
                    break
            if func_key is None:
                func_key = cname
            groups.setdefault(func_key, []).append(cname)
        return groups


def _parse_number_list(s: str) -> List[float]:
    """Parse a Liberty number list like \"0.01, 0.2727, 1.195\"."""
    parts = re.split(r",\s*", s.strip().strip('"'))
    vals = []
    for p in parts:
        p = p.strip()
        if p:
            try:
                vals.append(float(p))
            except ValueError:
                pass
    return vals


def _parse_values_block(lines: List[str]) -> List[List[float]]:
    """Parse the multi-line values(...) block in a Liberty table."""
    text = "\n".join(lines)
    text = text.replace("\\", "")
    # Extract everything inside values(...)
    m = re.search(r"values\s*\((.*)\)", text, re.DOTALL)
    if not m:
        return []
    inner = m.group(1)
    rows = []
    for row_str in inner.split('"'):
        row_str = row_str.strip().strip(",")
        if not row_str:
            continue
        rows.append(_parse_number_list(row_str))
    return rows


class _LibertyTokenizer:
    """Very small tokenizer that flattens braces and semicolons into tokens."""

    def __init__(self, text: str):
        self.tokens: List[str] = []
        self._tokenize(text)

    def _tokenize(self, text: str):
        # Remove C-style comments
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        text = re.sub(r"//.*?\n", "\n", text)
        # Tokenize: strings, identifiers/numbers, braces, colon, semicolon
        pattern = re.compile(
            r'"[^"]*"'  # strings
            r"|\(|\)|\{|\}|;|:"
            r"|[A-Za-z_][A-Za-z0-9_]*"  # identifiers
            r"|[+-]?\d+\.?\d*(?:[eE][+-]?\d+)?"  # numbers
            r"|[^\s\w\"();:{}]"  # single char operators like -, +, !, &, |, ^
        )
        i = 0
        while i < len(text):
            m = pattern.match(text, i)
            if m:
                tok = m.group(0)
                self.tokens.append(tok)
                i = m.end()
            else:
                i += 1


class _LibertyParser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> Optional[str]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self) -> Optional[str]:
        tok = self.peek()
        self.pos += 1
        return tok

    def expect(self, expected: str):
        tok = self.consume()
        if tok != expected:
            raise SyntaxError(f"Expected {expected!r}, got {tok!r} at pos {self.pos}")

    def parse_library(self) -> LibertyLibrary:
        lib_name = None
        while self.peek() is not None:
            tok = self.consume()
            if tok == "library":
                self.expect("(")
                lib_name = self.consume().strip('"')
                self.expect(")")
                self.expect("{")
                return self._parse_library_body(lib_name)
        raise SyntaxError("No library block found")

    def _consume_until(self, stop: str) -> str:
        parts = []
        while self.peek() != stop:
            tok = self.consume()
            if tok is None:
                break
            parts.append(tok)
        return "".join(parts)

    def _parse_library_body(self, name: str) -> LibertyLibrary:
        lib = LibertyLibrary(name=name)
        while self.peek() != "}":
            key = self.consume()
            if key is None:
                break
            if key == "cell":
                self.expect("(")
                cname = self.consume().strip('"')
                self.expect(")")
                self.expect("{")
                cell = self._parse_cell(cname)
                lib.cells[cname] = cell
            elif key == "time_unit":
                self.expect(":")
                lib.time_unit = self._consume_until(";").strip().strip('"')
                self.expect(";")
            elif key == "capacitive_load_unit":
                self.expect("(")
                val = float(self.consume())
                self.expect(",")
                unit = self.consume().strip('"')
                self.expect(")")
                self.expect(";")
                lib.capacitive_load_unit = (val, unit)
            else:
                self._skip_statement()
        self.expect("}")
        return lib

    def _parse_cell(self, cname: str) -> LibertyCell:
        cell = LibertyCell(name=cname)
        while self.peek() != "}":
            key = self.consume()
            if key is None:
                break
            if key == "area":
                self.expect(":")
                cell.area = float(self.consume())
                self.expect(";")
            elif key == "cell_leakage_power":
                self.expect(":")
                cell.leakage_power = float(self.consume())
                self.expect(";")
            elif key == "pin":
                self.expect("(")
                pname = self.consume().strip('"')
                self.expect(")")
                self.expect("{")
                pin = self._parse_pin(pname)
                cell.pins[pname] = pin
            else:
                self._skip_statement()
        self.expect("}")
        return cell

    def _parse_pin(self, pname: str) -> LibertyPin:
        pin = LibertyPin(name=pname)
        while self.peek() != "}":
            key = self.consume()
            if key is None:
                break
            if key == "direction":
                self.expect(":")
                pin.direction = self.consume().strip('"')
                self.expect(";")
            elif key == "capacitance":
                self.expect(":")
                pin.capacitance = float(self.consume())
                self.expect(";")
            elif key == "max_capacitance":
                self.expect(":")
                pin.max_capacitance = float(self.consume())
                self.expect(";")
            elif key == "function":
                self.expect(":")
                pin.function = self.consume().strip('"')
                self.expect(";")
            elif key == "timing":
                self.expect("(")
                self.expect(")")
                self.expect("{")
                timing = self._parse_timing()
                pin.timings.append(timing)
            else:
                self._skip_statement()
        self.expect("}")
        return pin

    def _parse_timing(self) -> LibertyTiming:
        timing = LibertyTiming()
        while self.peek() != "}":
            key = self.consume()
            if key is None:
                break
            if key == "related_pin":
                self.expect(":")
                timing.related_pin = self.consume().strip('"')
                self.expect(";")
            elif key == "timing_sense":
                self.expect(":")
                timing.timing_sense = self.consume().strip('"')
                self.expect(";")
            elif key == "timing_type":
                self.expect(":")
                timing.timing_type = self.consume().strip('"')
                self.expect(";")
            elif key in ("cell_rise", "cell_fall", "rise_transition", "fall_transition"):
                tbl = self._parse_table(key)
                setattr(timing, key, tbl)
            else:
                self._skip_statement()
        self.expect("}")
        return timing

    def _parse_table(self, tbl_name: str) -> LibertyTable:
        self.expect("(")
        template_name = self.consume().strip('"')
        self.expect(")")
        self.expect("{")
        tbl = LibertyTable(name=template_name)
        raw_lines: List[str] = []
        while self.peek() != "}":
            key = self.consume()
            if key is None:
                break
            if key in ("index_1", "index_2"):
                self.expect("(")
                # gather until )
                val_parts = []
                while self.peek() != ")":
                    val_parts.append(self.consume())
                self.expect(")")
                self.expect(";")
                val_str = "".join(val_parts).strip().strip('"')
                nums = _parse_number_list(val_str)
                if key == "index_1":
                    tbl.index_1 = nums
                else:
                    tbl.index_2 = nums
            elif key == "values":
                raw_lines.append(key)
                # gather until the matching );
                while True:
                    tok = self.consume()
                    if tok is None:
                        break
                    raw_lines.append(tok)
                    if tok == ";":
                        break
            else:
                self._skip_statement()
        self.expect("}")
        if raw_lines:
            tbl.values = _parse_values_block(raw_lines)
        return tbl

    def _skip_statement(self):
        """Skip a simple attribute or a block that we don't care about."""
        # We are at some key token; skip until ';' or matching '}'
        brace_depth = 0
        while True:
            tok = self.consume()
            if tok is None:
                break
            if tok == "{":
                brace_depth += 1
            elif tok == "}":
                if brace_depth == 0:
                    # Should not happen at top-level skip, but handle gracefully
                    self.pos -= 1  # put back
                    break
                brace_depth -= 1
                if brace_depth == 0:
                    # after a block we often have ';'
                    if self.peek() == ";":
                        self.consume()
                    break
            elif tok == ";" and brace_depth == 0:
                break


def parse_liberty(path: str) -> LibertyLibrary:
    text = Path(path).read_text()
    toks = _LibertyTokenizer(text)
    parser = _LibertyParser(toks.tokens)
    return parser.parse_library()


def generate_demo_liberty(path: Optional[str] = None) -> str:
    """保留向后兼容的 demo Liberty 生成器。"""
    demo = """library (demo_tech) {
  technology (cmos);
  delay_model : table_lookup;
  time_unit : "1ns";
  voltage_unit : "1V";
  current_unit : "1uA";
  leakage_power_unit : "1nW";
  capacitive_load_unit (1,pf);

  cell (INVX1) {
    area : 1.0;
    pin (A) {
      direction : input;
      capacitance : 0.01;
    }
    pin (Y) {
      direction : output;
      function : "!A";
      timing () {
        related_pin : "A";
        cell_rise : 0.05;
        cell_fall : 0.05;
      }
    }
  }

  cell (NAND2X1) {
    area : 1.5;
    pin (A) {
      direction : input;
      capacitance : 0.01;
    }
    pin (B) {
      direction : input;
      capacitance : 0.01;
    }
    pin (Y) {
      direction : output;
      function : "!(A&B)";
      timing () {
        related_pin : "A";
        cell_rise : 0.08;
        cell_fall : 0.08;
      }
      timing () {
        related_pin : "B";
        cell_rise : 0.08;
        cell_fall : 0.08;
      }
    }
  }

  cell (NOR2X1) {
    area : 1.5;
    pin (A) {
      direction : input;
      capacitance : 0.01;
    }
    pin (B) {
      direction : input;
      capacitance : 0.01;
    }
    pin (Y) {
      direction : output;
      function : "!(A|B)";
      timing () {
        related_pin : "A";
        cell_rise : 0.08;
        cell_fall : 0.08;
      }
      timing () {
        related_pin : "B";
        cell_rise : 0.08;
        cell_fall : 0.08;
      }
    }
  }

  cell (DFFX1) {
    area : 4.0;
    pin (D) {
      direction : input;
      capacitance : 0.02;
    }
    pin (CK) {
      direction : input;
      capacitance : 0.02;
    }
    pin (Q) {
      direction : output;
      function : "IQ";
      timing () {
        related_pin : "CK";
        timing_type : rising_edge;
        cell_rise : 0.10;
        cell_fall : 0.10;
      }
    }
  }
}
"""
    if path is not None:
        Path(path).write_text(demo)
    return demo


def generate_sizing_demo_liberty(path: Optional[str] = None) -> str:
    """生成带 drive-strength 变体的 demo Liberty，用于测试 Gate Sizing。"""
    def _inv_cell(name: str, area: float, delay_scale: float, cap: float):
        return f"""  cell ({name}) {{
    area : {area};
    pin (A) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (Y) {{
      direction : output;
      function : "!A";
      max_capacitance : 0.1;
      timing () {{
        related_pin : "A";
        timing_sense : negative_unate;
        cell_rise(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.05*delay_scale:.4f}, {0.08*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.12*delay_scale:.4f}");
        }}
        cell_fall(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.05*delay_scale:.4f}, {0.08*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.12*delay_scale:.4f}");
        }}
        rise_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.04*delay_scale:.4f}, {0.06*delay_scale:.4f}",
                 "{0.05*delay_scale:.4f}, {0.08*delay_scale:.4f}");
        }}
        fall_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.04*delay_scale:.4f}, {0.06*delay_scale:.4f}",
                 "{0.05*delay_scale:.4f}, {0.08*delay_scale:.4f}");
        }}
      }}
    }}
  }}
"""

    def _nand2_cell(name: str, area: float, delay_scale: float, cap: float):
        return f"""  cell ({name}) {{
    area : {area};
    pin (A) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (B) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (Y) {{
      direction : output;
      function : "!(A&B)";
      max_capacitance : 0.1;
      timing () {{
        related_pin : "A";
        cell_rise(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}",
                 "{0.10*delay_scale:.4f}, {0.18*delay_scale:.4f}");
        }}
        cell_fall(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}",
                 "{0.10*delay_scale:.4f}, {0.18*delay_scale:.4f}");
        }}
        rise_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.06*delay_scale:.4f}, {0.09*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}");
        }}
        fall_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.06*delay_scale:.4f}, {0.09*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}");
        }}
      }}
    }}
  }}
"""

    def _nor2_cell(name: str, area: float, delay_scale: float, cap: float):
        return f"""  cell ({name}) {{
    area : {area};
    pin (A) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (B) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (Y) {{
      direction : output;
      function : "!(A|B)";
      max_capacitance : 0.1;
      timing () {{
        related_pin : "A";
        cell_rise(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}",
                 "{0.10*delay_scale:.4f}, {0.18*delay_scale:.4f}");
        }}
        cell_fall(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}",
                 "{0.10*delay_scale:.4f}, {0.18*delay_scale:.4f}");
        }}
        rise_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.06*delay_scale:.4f}, {0.09*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}");
        }}
        fall_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.06*delay_scale:.4f}, {0.09*delay_scale:.4f}",
                 "{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}");
        }}
      }}
    }}
  }}
"""

    lib = """library (sizing_demo) {
  technology (cmos);
  delay_model : table_lookup;
  time_unit : "1ns";
  voltage_unit : "1V";
  current_unit : "1uA";
  leakage_power_unit : "1nW";
  capacitive_load_unit (1,pf);

  lu_table_template(tmg) {
    variable_1 : input_net_transition;
    variable_2 : total_output_net_capacitance;
    index_1("0.01, 0.1");
    index_2("0.01, 0.1");
  }

"""
    def _nand3_cell(name: str, area: float, delay_scale: float, cap: float):
        return f"""  cell ({name}) {{
    area : {area};
    pin (A) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (B) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (C) {{
      direction : input;
      capacitance : {cap};
    }}
    pin (Y) {{
      direction : output;
      function : "!(A&B&C)";
      max_capacitance : 0.1;
      timing () {{
        related_pin : "A";
        cell_rise(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.10*delay_scale:.4f}, {0.16*delay_scale:.4f}",
                 "{0.12*delay_scale:.4f}, {0.22*delay_scale:.4f}");
        }}
        cell_fall(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.10*delay_scale:.4f}, {0.16*delay_scale:.4f}",
                 "{0.12*delay_scale:.4f}, {0.22*delay_scale:.4f}");
        }}
        rise_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}",
                 "{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}");
        }}
        fall_transition(tmg) {{
          index_1("0.01, 0.1");
          index_2("0.01, 0.1");
          values("{0.07*delay_scale:.4f}, {0.11*delay_scale:.4f}",
                 "{0.08*delay_scale:.4f}, {0.13*delay_scale:.4f}");
        }}
      }}
    }}
  }}
"""

    lib += _inv_cell("INVX1", 1.0, 1.0, 0.01)
    lib += _inv_cell("INVX2", 1.4, 0.7, 0.015)
    lib += _inv_cell("INVX4", 2.2, 0.5, 0.025)
    lib += _nand2_cell("NAND2X1", 1.5, 1.0, 0.01)
    lib += _nand2_cell("NAND2X2", 2.1, 0.7, 0.015)
    lib += _nor2_cell("NOR2X1", 1.5, 1.0, 0.01)
    lib += _nor2_cell("NOR2X2", 2.1, 0.7, 0.015)
    lib += _nand3_cell("NAND3X1", 2.0, 1.0, 0.01)
    lib += """}
"""
    if path is not None:
        Path(path).write_text(lib)
    return lib
