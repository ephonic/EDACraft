"""
rtlgen.regmodel — Register Abstraction Layer (RAL) 描述

用于定义寄存器、字段和寄存器块，供 UVMEmitter 生成 UVM RAL 模型。
"""
from __future__ import annotations

from typing import List, Optional, Tuple


class RegField:
    """寄存器字段描述。"""

    def __init__(
        self,
        name: str,
        width: int,
        access: str = "RW",
        reset: int = 0,
        desc: str = "",
    ):
        self.name = name
        self.width = width
        self.access = access
        self.reset = reset
        self.desc = desc


class Register:
    """寄存器描述。"""

    def __init__(self, name: str, width: int = 32, fields: Optional[List[RegField]] = None):
        self.name = name
        self.width = width
        if fields is None:
            self.fields = [RegField(name, width, access="RW", reset=0)]
        else:
            self.fields = fields
            total = sum(f.width for f in self.fields)
            if total != width:
                raise ValueError(
                    f"Register '{name}' fields total width ({total}) != register width ({width})"
                )


class RegBlock:
    """寄存器块描述。"""

    def __init__(self, name: str, base_addr: int = 0, registers: Optional[List[Tuple[Register, int]]] = None):
        self.name = name
        self.base_addr = base_addr
        self.registers: List[Tuple[Register, int]] = list(registers) if registers else []

    def add_reg(self, reg: Register, offset: int):
        """添加寄存器及其偏移地址。"""
        self.registers.append((reg, offset))
