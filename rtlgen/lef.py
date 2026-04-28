"""
rtlgen.lef — LEF (Library Exchange Format) data model, demo generator, and parser.

Supports:
- SITE, MACRO, PIN, LAYER definitions
- Simplified geometry (RECT only)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class LefRect:
    layer: str
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class LefPin:
    name: str
    direction: str = ""  # INPUT, OUTPUT, INOUT
    use: str = "SIGNAL"
    shapes: List[LefRect] = field(default_factory=list)


@dataclass
class LefMacro:
    name: str
    macro_class: str = "CORE"
    foreign: Optional[str] = None
    origin: tuple = (0.0, 0.0)
    size: tuple = (1.0, 1.0)
    symmetry: List[str] = field(default_factory=list)
    site: Optional[str] = None
    pins: Dict[str, LefPin] = field(default_factory=dict)
    obs: List[LefRect] = field(default_factory=list)


@dataclass
class LefLayer:
    name: str
    layer_type: str  # ROUTING, CUT, MASTERSLICE, OVERLAP
    direction: Optional[str] = None  # HORIZONTAL, VERTICAL
    pitch: float = 1.0
    width: float = 0.1
    spacing: float = 0.1


@dataclass
class LefSite:
    name: str
    site_class: str = "CORE"
    symmetry: str = "X Y"
    size: tuple = (1.0, 1.0)


@dataclass
class LefLibrary:
    version: str = "5.7"
    bus_bit_chars: str = "[]"
    divider_char: str = "/"
    units: Dict[str, float] = field(default_factory=dict)
    sites: Dict[str, LefSite] = field(default_factory=dict)
    layers: Dict[str, LefLayer] = field(default_factory=dict)
    macros: Dict[str, LefMacro] = field(default_factory=dict)

    def get_site_height(self) -> float:
        """Return the height of the first CORE site."""
        for site in self.sites.values():
            if site.site_class == "CORE":
                return site.size[1]
        return 1.0


def generate_demo_lef(path: Optional[str] = None) -> str:
    """生成一个极简的 demo LEF，包含 3 个标准单元和 2 层金属。"""
    lef = """VERSION 5.7 ;
BUSBITCHARS "[]" ;
DIVIDERCHAR "/" ;

UNITS
  DATABASE MICRONS 1000 ;
END UNITS

SITE CORE
  CLASS CORE ;
  SYMMETRY X Y ;
  SIZE 1.000 BY 1.000 ;
END CORE

LAYER metal1
  TYPE ROUTING ;
  DIRECTION HORIZONTAL ;
  PITCH 1.0 ;
  WIDTH 0.14 ;
  SPACING 0.14 ;
END metal1

LAYER metal2
  TYPE ROUTING ;
  DIRECTION VERTICAL ;
  PITCH 1.0 ;
  WIDTH 0.14 ;
  SPACING 0.14 ;
END metal2

MACRO INVX1
  CLASS CORE ;
  FOREIGN INVX1 0 0 ;
  ORIGIN 0 0 ;
  SIZE 1.000 BY 1.000 ;
  SYMMETRY X Y ;
  SITE CORE ;
  PIN A
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.100 0.100 0.300 0.300 ;
    END PORT
  END A
  PIN Y
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.700 0.700 0.900 0.900 ;
    END PORT
  END Y
  OBS
    LAYER metal1 ;
      RECT 0.000 0.000 1.000 1.000 ;
  END OBS
END INVX1

MACRO NAND2X1
  CLASS CORE ;
  FOREIGN NAND2X1 0 0 ;
  ORIGIN 0 0 ;
  SIZE 1.500 BY 1.000 ;
  SYMMETRY X Y ;
  SITE CORE ;
  PIN A
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.100 0.100 0.300 0.300 ;
    END PORT
  END A
  PIN B
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.400 0.100 0.600 0.300 ;
    END PORT
  END B
  PIN Y
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 1.200 0.700 1.400 0.900 ;
    END PORT
  END Y
  OBS
    LAYER metal1 ;
      RECT 0.000 0.000 1.500 1.000 ;
  END OBS
END NAND2X1

MACRO NOR2X1
  CLASS CORE ;
  FOREIGN NOR2X1 0 0 ;
  ORIGIN 0 0 ;
  SIZE 1.500 BY 1.000 ;
  SYMMETRY X Y ;
  SITE CORE ;
  PIN A
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.100 0.100 0.300 0.300 ;
    END PORT
  END A
  PIN B
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.400 0.100 0.600 0.300 ;
    END PORT
  END B
  PIN Y
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 1.200 0.700 1.400 0.900 ;
    END PORT
  END Y
  OBS
    LAYER metal1 ;
      RECT 0.000 0.000 1.500 1.000 ;
  END OBS
END NOR2X1

MACRO NAND3X1
  CLASS CORE ;
  FOREIGN NAND3X1 0 0 ;
  ORIGIN 0 0 ;
  SIZE 2.000 BY 1.000 ;
  SYMMETRY X Y ;
  SITE CORE ;
  PIN A
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.100 0.100 0.300 0.300 ;
    END PORT
  END A
  PIN B
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.500 0.100 0.700 0.300 ;
    END PORT
  END B
  PIN C
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 0.900 0.100 1.100 0.300 ;
    END PORT
  END C
  PIN Y
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER metal1 ;
        RECT 1.700 0.700 1.900 0.900 ;
    END PORT
  END Y
  OBS
    LAYER metal1 ;
      RECT 0.000 0.000 2.000 1.000 ;
  END OBS
END NAND3X1

END LIBRARY
"""
    if path is not None:
        Path(path).write_text(lef)
    return lef


def parse_lef(path: str) -> LefLibrary:
    """Very small LEF parser for demo / educational use."""
    text = Path(path).read_text()
    lines = text.splitlines()
    lib = LefLibrary()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue

        if line.startswith("VERSION"):
            lib.version = line.replace("VERSION", "").replace(";", "").strip()
        elif line.startswith("BUSBITCHARS"):
            lib.bus_bit_chars = line.split('"')[1]
        elif line.startswith("DIVIDERCHAR"):
            lib.divider_char = line.split('"')[1]
        elif line.startswith("SITE"):
            name = line.split()[1]
            site = LefSite(name=name)
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("END " + name):
                tok = lines[i].strip().split()
                if tok[0] == "CLASS":
                    site.site_class = tok[1]
                elif tok[0] == "SYMMETRY":
                    site.symmetry = " ".join(tok[1:])
                elif tok[0] == "SIZE":
                    site.size = (float(tok[1]), float(tok[3]))
                i += 1
            lib.sites[name] = site
        elif line.startswith("LAYER"):
            name = line.split()[1]
            layer = LefLayer(name=name, layer_type="ROUTING")
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("END " + name):
                tok = lines[i].strip().split()
                if tok[0] == "TYPE":
                    layer.layer_type = tok[1]
                elif tok[0] == "DIRECTION":
                    layer.direction = tok[1]
                elif tok[0] == "PITCH":
                    layer.pitch = float(tok[1])
                elif tok[0] == "WIDTH":
                    layer.width = float(tok[1])
                elif tok[0] == "SPACING":
                    layer.spacing = float(tok[1])
                i += 1
            lib.layers[name] = layer
        elif line.startswith("MACRO"):
            name = line.split()[1]
            macro = LefMacro(name=name)
            i += 1
            current_pin = None
            in_port = False
            while i < len(lines) and not lines[i].strip().startswith("END " + name):
                tok = lines[i].strip().split()
                if not tok:
                    i += 1
                    continue
                if tok[0] == "CLASS":
                    macro.macro_class = tok[1]
                elif tok[0] == "FOREIGN":
                    macro.foreign = tok[1]
                elif tok[0] == "ORIGIN":
                    macro.origin = (float(tok[1]), float(tok[2]))
                elif tok[0] == "SIZE":
                    macro.size = (float(tok[1]), float(tok[3]))
                elif tok[0] == "SYMMETRY":
                    macro.symmetry = tok[1:]
                elif tok[0] == "SITE":
                    macro.site = tok[1]
                elif tok[0] == "PIN":
                    pin_name = tok[1]
                    current_pin = LefPin(name=pin_name)
                    in_port = False
                elif tok[0] == "DIRECTION" and current_pin is not None:
                    current_pin.direction = tok[1]
                elif tok[0] == "USE" and current_pin is not None:
                    current_pin.use = tok[1]
                elif tok[0] == "PORT":
                    in_port = True
                elif tok[0] == "END" and current_pin is not None and tok[1] == "PORT":
                    in_port = False
                elif tok[0] == "END" and current_pin is not None and tok[1] == current_pin.name:
                    macro.pins[current_pin.name] = current_pin
                    current_pin = None
                elif tok[0] == "RECT" and in_port and current_pin is not None:
                    # last seen layer
                    layer_name = "metal1"
                    current_pin.shapes.append(
                        LefRect(layer_name, float(tok[1]), float(tok[2]), float(tok[3]), float(tok[4]))
                    )
                elif tok[0] == "LAYER" and in_port and current_pin is not None:
                    # store for next RECT
                    pass
                elif tok[0] == "RECT" and current_pin is None:
                    # OBS rect
                    layer_name = "metal1"
                    macro.obs.append(
                        LefRect(layer_name, float(tok[1]), float(tok[2]), float(tok[3]), float(tok[4]))
                    )
                i += 1
            lib.macros[name] = macro
        i += 1
    return lib
