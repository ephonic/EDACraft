#!/usr/bin/env python3
"""Drive STA from Python with no hand-written SDC file.

source /apps/EDAs/own/ftimer/env.sh
python python_constraints.py --liberty cells.lib --verilog design.v \
    --clock-port clk --period 1.25 --input-port a --input-port b --output-port z
Omit --clock-port to create a virtual I/O clock.
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ftimer import FTimer, SDC, get_ports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--liberty', action='append', required=True)
    parser.add_argument('--verilog', required=True)
    parser.add_argument('--spef')
    parser.add_argument('--clock-port')
    parser.add_argument('--period', type=float, required=True, help='clock period in ns')
    parser.add_argument('--input-port', action='append', required=True, help='repeat for data inputs')
    parser.add_argument('--output-port', action='append', required=True)
    parser.add_argument('--input-delay', type=float, default=.1, help='ns')
    parser.add_argument('--output-delay', type=float, default=.1, help='ns')
    parser.add_argument('--input-slew', type=float, default=.02, help='ns')
    parser.add_argument('--load', type=float, default=.01, help='pF')
    parser.add_argument('--export-sdc', type=Path)
    args = parser.parse_args()

    sdc = SDC()
    sdc.create_clock('clk', args.period, args.clock_port)
    sdc.set_input_delay(args.input_delay, get_ports(args.input_port), clock='clk')
    sdc.set_output_delay(args.output_delay, get_ports(args.output_port), clock='clk')
    sdc.set_input_transition(args.input_slew, get_ports(args.input_port))
    sdc.set_load(args.load, get_ports(args.output_port))
    timer = FTimer(liberty=args.liberty, verilog=args.verilog,
                   spef=args.spef or (), constraints=sdc)
    if args.export_sdc:
        timer.write_sdc(args.export_sdc)
    print(timer.report_timing(max_paths=10, min_paths=10))


if __name__ == '__main__':
    main()
