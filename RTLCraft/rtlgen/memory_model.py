"""
rtlgen.memory_model — Byte-addressable memory with alignment, endianness, and atomics.

Supports any word size (8/16/32/64/128/...), unaligned access (optional),
big/little endian, and atomic operations (LR/SC, AMO).

This is a cycle-accurate behavioral model, not a timing model.
It tracks memory state precisely for golden-reference simulation.
"""
from __future__ import annotations

import struct
from typing import Dict, List, Optional, Tuple


class MemoryAccessError(Exception):
    """Raised on invalid memory access (alignment, out-of-bounds, permission)."""
    pass


class MemoryModel:
    """Byte-addressable flat memory with configurable policies.

    Usage:
        mem = MemoryModel(size=2**32, base_addr=0x8000_0000)
        mem.write(0x8000_0000, 0x1234_5678, size=4)
        val = mem.read(0x8000_0000, size=4)  # -> 0x1234_5678
    """

    def __init__(
        self,
        size: int = 2**32,
        base_addr: int = 0,
        little_endian: bool = True,
        enforce_alignment: bool = False,
        init_file: Optional[str] = None,
    ):
        self.size = size
        self.base_addr = base_addr
        self.little_endian = little_endian
        self.enforce_alignment = enforce_alignment
        # Sparse storage: only allocate pages on write
        self._pages: Dict[int, bytearray] = {}
        self._page_size = 4096
        self._page_mask = self._page_size - 1

        # Atomic reservation set (for LR/SC)
        self._reservations: Dict[int, Tuple[int, int]] = {}  # hart_id -> (addr, size)

        if init_file:
            self._load_init_file(init_file)

    # -----------------------------------------------------------------
    # Core access
    # -----------------------------------------------------------------
    def read(self, addr: int, size: int = 4) -> int:
        """Read `size` bytes from `addr`, return as unsigned integer."""
        if size not in (1, 2, 4, 8, 16):
            raise MemoryAccessError(f"Unsupported read size: {size}")
        if self.enforce_alignment and addr % size != 0:
            raise MemoryAccessError(f"Unaligned read: addr={addr:#x}, size={size}")
        offset = addr - self.base_addr
        if offset < 0 or offset + size > self.size:
            raise MemoryAccessError(f"Out of bounds read: addr={addr:#x}, size={size}")

        data = self._read_bytes(offset, size)
        return self._bytes_to_int(data, size)

    def write(self, addr: int, value: int, size: int = 4) -> None:
        """Write `size` bytes of `value` to `addr`."""
        if size not in (1, 2, 4, 8, 16):
            raise MemoryAccessError(f"Unsupported write size: {size}")
        if self.enforce_alignment and addr % size != 0:
            raise MemoryAccessError(f"Unaligned write: addr={addr:#x}, size={size}")
        offset = addr - self.base_addr
        if offset < 0 or offset + size > self.size:
            raise MemoryAccessError(f"Out of bounds write: addr={addr:#x}, size={size}")

        data = self._int_to_bytes(value, size)
        self._write_bytes(offset, data)

    def read_signed(self, addr: int, size: int = 4) -> int:
        """Read `size` bytes and sign-extend."""
        val = self.read(addr, size)
        msb = 1 << (size * 8 - 1)
        if val & msb:
            val -= (1 << (size * 8))
        return val

    # -----------------------------------------------------------------
    # Atomic operations
    # -----------------------------------------------------------------
    def atomic_lr(self, addr: int, size: int = 4, hart_id: int = 0) -> int:
        """Load-Reserved: load value and reserve address for this hart."""
        self._reservations[hart_id] = (addr, size)
        return self.read(addr, size)

    def atomic_sc(self, addr: int, value: int, size: int = 4, hart_id: int = 0) -> bool:
        """Store-Conditional: store only if reservation is still valid.
        Returns True on success, False on failure."""
        reserved = self._reservations.get(hart_id)
        if reserved is None or reserved != (addr, size):
            return False
        # Clear all reservations on this address (any size overlapping)
        self._clear_reservations_at(addr, size)
        self.write(addr, value, size)
        return True

    def atomic_amo(self, addr: int, value: int, op: str, size: int = 4) -> int:
        """Atomic Memory Operation: read old value, apply op, write new value.
        Returns old value.

        Supported ops: swap, add, xor, and, or, min, max, minu, maxu
        """
        old = self.read(addr, size)
        mask = (1 << (size * 8)) - 1
        signed_old = old if old < (1 << (size * 8 - 1)) else old - (1 << (size * 8))
        signed_val = value if value < (1 << (size * 8 - 1)) else value - (1 << (size * 8))

        if op == "swap":
            new = value
        elif op == "add":
            new = (old + value) & mask
        elif op == "xor":
            new = (old ^ value) & mask
        elif op == "and":
            new = (old & value) & mask
        elif op == "or":
            new = (old | value) & mask
        elif op == "min":
            new = signed_old if signed_old < signed_val else signed_val
            new &= mask
        elif op == "max":
            new = signed_old if signed_old > signed_val else signed_val
            new &= mask
        elif op == "minu":
            new = old if old < value else value
        elif op == "maxu":
            new = old if old > value else value
        else:
            raise MemoryAccessError(f"Unknown AMO op: {op}")

        self.write(addr, new, size)
        return old

    # -----------------------------------------------------------------
    # Bulk operations
    # -----------------------------------------------------------------
    def read_block(self, addr: int, size: int) -> bytes:
        """Read a contiguous block of bytes."""
        offset = addr - self.base_addr
        if offset < 0 or offset + size > self.size:
            raise MemoryAccessError(f"Out of bounds block read: addr={addr:#x}, size={size}")
        return self._read_bytes(offset, size)

    def write_block(self, addr: int, data: bytes) -> None:
        """Write a contiguous block of bytes."""
        offset = addr - self.base_addr
        if offset < 0 or offset + len(data) > self.size:
            raise MemoryAccessError(f"Out of bounds block write: addr={addr:#x}, size={len(data)}")
        self._write_bytes(offset, data)

    def load_elf(self, path: str) -> None:
        """Load an ELF file into memory at its segment base addresses."""
        # Minimal ELF loader (32-bit and 64-bit)
        with open(path, "rb") as f:
            data = f.read()

        if data[:4] != b"\x7fELF":
            raise MemoryAccessError(f"Not an ELF file: {path}")

        ei_class = data[4]
        is_64 = ei_class == 2

        if is_64:
            e_phoff = int.from_bytes(data[32:40], "little")
            e_phentsize = int.from_bytes(data[54:56], "little")
            e_phnum = int.from_bytes(data[56:58], "little")
        else:
            e_phoff = int.from_bytes(data[28:32], "little")
            e_phentsize = int.from_bytes(data[42:44], "little")
            e_phnum = int.from_bytes(data[44:46], "little")

        for i in range(e_phnum):
            off = e_phoff + i * e_phentsize
            p_type = int.from_bytes(data[off:off+4], "little")
            if p_type != 1:  # PT_LOAD
                continue
            if is_64:
                p_vaddr = int.from_bytes(data[off+16:off+24], "little")
                p_filesz = int.from_bytes(data[off+32:off+40], "little")
                p_offset = int.from_bytes(data[off+8:off+16], "little")
            else:
                p_vaddr = int.from_bytes(data[off+8:off+12], "little")
                p_filesz = int.from_bytes(data[off+16:off+20], "little")
                p_offset = int.from_bytes(data[off+4:off+8], "little")

            seg_data = data[p_offset:p_offset + p_filesz]
            self.write_block(p_vaddr, seg_data)

    # -----------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------
    def _page_idx(self, offset: int) -> int:
        return offset // self._page_size

    def _page_off(self, offset: int) -> int:
        return offset & self._page_mask

    def _ensure_page(self, page_idx: int):
        if page_idx not in self._pages:
            self._pages[page_idx] = bytearray(self._page_size)

    def _read_bytes(self, offset: int, size: int) -> bytes:
        result = bytearray(size)
        for i in range(size):
            page_idx = self._page_idx(offset + i)
            page = self._pages.get(page_idx)
            if page is None:
                result[i] = 0
            else:
                result[i] = page[self._page_off(offset + i)]
        return bytes(result)

    def _write_bytes(self, offset: int, data: bytes):
        for i, b in enumerate(data):
            page_idx = self._page_idx(offset + i)
            self._ensure_page(page_idx)
            self._pages[page_idx][self._page_off(offset + i)] = b

    def _bytes_to_int(self, data: bytes, size: int) -> int:
        if self.little_endian:
            return int.from_bytes(data, "little")
        else:
            return int.from_bytes(data, "big")

    def _int_to_bytes(self, value: int, size: int) -> bytes:
        if self.little_endian:
            return value.to_bytes(size, "little")
        else:
            return value.to_bytes(size, "big")

    def _clear_reservations_at(self, addr: int, size: int):
        """Clear all reservations overlapping [addr, addr+size)."""
        to_remove = []
        for hart_id, (r_addr, r_size) in list(self._reservations.items()):
            if not (r_addr + r_size <= addr or r_addr >= addr + size):
                to_remove.append(hart_id)
        for hart_id in to_remove:
            del self._reservations[hart_id]

    def _load_init_file(self, path: str):
        """Load a hex file (one value per line) into memory starting at base_addr."""
        with open(path, "r") as f:
            addr = 0
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("@"):
                    addr = int(line[1:], 16)
                    continue
                val = int(line, 16)
                self.write(self.base_addr + addr, val, size=4)
                addr += 4
