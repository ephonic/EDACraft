# skills.interfaces.spi — SPI Master/Slave Interface

Clean-room Python DSL redesign of the open-source **verilog_spi** project.

## Original Reference

- **Project**: verilog_spi
- **Author**: Dr. med. Jan Schiefer
- **License**: LGPL-2.1
- **Repository**: https://github.com/drjc/verilog_spi (inferred)
- **Local ref_rtl**: `ref_rtl/interfaces/spi/`

The original Verilog implementation supports:
- SPI master / slave mode
- All 4 SPI modes (CPOL / CPHA combinations)
- Inverted data order (LSB first)
- Configurable word length

## DSL Modules

| Module | Description |
|--------|-------------|
| `PosEdgeDetector` | One-cycle pulse on rising edge |
| `NegEdgeDetector` | One-cycle pulse on falling edge |
| `SPIClockDivider` | Free-running counter clock divider (`2^DIV_N`) |
| `SPIModule` | Core SPI master/slave with FSM |
| `SPITop` | Top-level with integrated clock divider |

## Usage

```python
from skills.interfaces.spi import SPITop

spi = SPITop(
    cpol=0, cpha=0,           # SPI Mode 0
    spi_master=1,             # Master mode
    spi_word_len=8,           # 8-bit words
    clk_div_n=4,              # SCLK = clk / 16
)
```

## Copyright Notice

The original Verilog reference designs under `ref_rtl/interfaces/spi/` are
copyright of Dr. med. Jan Schiefer and licensed under the GNU Lesser General
Public License v2.1. The Python DSL modules in this directory are a clean-room
re-implementation inspired by the reference design, retaining compatibility with
the original interface semantics.

> **License Compliance Notice**
>
> The reference RTL designs that inspired this skill are copyrighted by their
> original authors. Before using this skill, please review and comply with the
> license terms listed in the "Project Source" section above. If no license is
> specified, contact the original author for permission.
