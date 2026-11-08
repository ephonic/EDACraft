"""Python descriptions of the SDC subset implemented by ftimer.

Time values are in ns and capacitances in pF. Collections describe selectors;
they are resolved against the loaded netlist by the timing engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Union


def _name(value: str) -> str:
    if not isinstance(value, str) or not value or any(
        c.isspace() or c in '{};"$\\#' or ord(c) < 32 for c in value
    ) or value.startswith('-'):
        raise ValueError("object names must be nonempty tokens; pass multiple names as a sequence")
    return value


def _number(value: float, *, minimum: float | None = None) -> str:
    if isinstance(value, (bool, str, bytes)):
        raise ValueError("expected a finite number")
    number = float(value)
    if not math.isfinite(number) or (minimum is not None and number < minimum):
        raise ValueError(f"expected a finite number >= {minimum}" if minimum is not None
                         else "expected a finite number")
    return str(number)


def _choice(value: str, choices: Sequence[str]) -> str:
    if value not in choices:
        raise ValueError(f"expected one of {', '.join(choices)}; got {value!r}")
    return value


@dataclass(frozen=True)
class SdcCollection:
    kind: str
    names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _choice(self.kind, ('ports', 'pins', 'clocks', 'all_inputs', 'all_outputs'))
        names = tuple(_name(name) for name in self.names)
        object.__setattr__(self, 'names', names)
        if bool(names) == self.kind.startswith('all_'):
            raise ValueError("get_* collections need names; all_* collections take no names")

    def to_sdc(self) -> str:
        if self.kind.startswith('all_'):
            return f'[{self.kind}]'
        return f'[get_{self.kind} {{{" ".join(self.names)}}}]'


def _collection(kind: str, names: str | Sequence[str]) -> SdcCollection:
    return SdcCollection(kind, (names,) if isinstance(names, str) else tuple(names))


def get_ports(names: str | Sequence[str]) -> SdcCollection:
    return _collection('ports', names)


def get_pins(names: str | Sequence[str]) -> SdcCollection:
    return _collection('pins', names)


def get_clocks(names: str | Sequence[str]) -> SdcCollection:
    return _collection('clocks', names)


def all_inputs() -> SdcCollection:
    return SdcCollection('all_inputs')


def all_outputs() -> SdcCollection:
    return SdcCollection('all_outputs')


Selection = Union[SdcCollection, str, Sequence[str]]


def _select(value: Selection, *, default: str = 'ports',
            allowed: Sequence[str] = ('ports', 'pins', 'clocks', 'all_inputs', 'all_outputs')) -> SdcCollection:
    selection = value if isinstance(value, SdcCollection) else _collection(default, value)
    if selection.kind not in allowed:
        raise ValueError(f"expected a selector of type {', '.join(allowed)}")
    return selection


def _flags(analysis: str, transition: str = 'both') -> list[str]:
    _choice(analysis, ('both', 'min', 'max'))
    _choice(transition, ('both', 'rise', 'fall'))
    return ([] if analysis == 'both' else ['-'+analysis]) + (
        [] if transition == 'both' else ['-'+transition])


class SDC:
    """Ordered, mutable Python constraints; methods return self for chaining.

    Numeric time values always mean ns, capacitance values pF. This API covers
    the explicitly implemented methods, rather than arbitrary Tcl commands.
    Use normal Python loops/functions to construct or sweep constraints.
    """

    def __init__(self) -> None:
        self._commands: list[str] = []

    def __bool__(self) -> bool:
        return bool(self._commands)

    def _add(self, *words: str) -> SDC:
        self._commands.append(' '.join(words))
        return self

    def to_sdc(self) -> str:
        return 'set_units -time ns -capacitance pF\n' + '\n'.join(self._commands) + '\n'

    def write(self, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(self.to_sdc(), encoding='utf-8')
        return path

    def create_clock(self, name: str, period: float, ports: Selection | None = None,
                     *, waveform: Sequence[float] | None = None) -> SDC:
        period_text = _number(period, minimum=0)
        if float(period_text) == 0:
            raise ValueError('clock period must be positive')
        words = ['create_clock', '-name', '{'+_name(name)+'}', '-period', period_text]
        if waveform is not None:
            if len(waveform) != 2:
                raise ValueError('waveform must contain rise and fall edges')
            rise, fall = (_number(edge, minimum=0) for edge in waveform)
            if not 0 <= float(rise) < float(fall) <= float(period_text):
                raise ValueError('waveform must satisfy 0 <= rise < fall <= period')
            words += ['-waveform', '{'+rise+' '+fall+'}']
        if ports is not None:
            selection = _select(ports, allowed=('ports', 'pins'))
            if len(selection.names) != 1:
                raise ValueError('create_clock requires one source port or pin')
            words.append(selection.to_sdc())
        return self._add(*words)

    def _io_delay(self, command: str, delay: float, ports: Selection, clock: str,
                  analysis: str, transition: str) -> SDC:
        return self._add(command, '-clock', '{'+_name(clock)+'}', *_flags(analysis, transition),
                         _number(delay), _select(ports, allowed=('ports', 'all_inputs', 'all_outputs')).to_sdc())

    def set_input_delay(self, delay: float, ports: Selection, *, clock: str,
                        analysis: str = 'both', transition: str = 'both') -> SDC:
        return self._io_delay('set_input_delay', delay, ports, clock, analysis, transition)

    def set_output_delay(self, delay: float, ports: Selection, *, clock: str,
                         analysis: str = 'both', transition: str = 'both') -> SDC:
        return self._io_delay('set_output_delay', delay, ports, clock, analysis, transition)

    def set_input_transition(self, transition: float, ports: Selection, *,
                             analysis: str = 'both', edge: str = 'both') -> SDC:
        return self._add('set_input_transition', *_flags(analysis, edge), _number(transition, minimum=0),
                         _select(ports, allowed=('ports', 'all_inputs')).to_sdc())

    def set_load(self, capacitance: float, ports: Selection) -> SDC:
        return self._add('set_load', _number(capacitance, minimum=0),
                         _select(ports, allowed=('ports', 'pins', 'all_outputs')).to_sdc())

    def set_driving_cell(self, lib_cell: str, ports: Selection, *, library: str | None = None,
                         pin: str | None = None, from_pin: str | None = None,
                         input_transition_rise: float | None = None,
                         input_transition_fall: float | None = None,
                         analysis: str = 'both', transition: str = 'both') -> SDC:
        words = ['set_driving_cell', '-lib_cell', _name(lib_cell), *_flags(analysis, transition)]
        for option, value in [('library', library), ('pin', pin), ('from_pin', from_pin)]:
            if value is not None:
                words += ['-'+option, _name(value)]
        for option, value in [('input_transition_rise', input_transition_rise),
                              ('input_transition_fall', input_transition_fall)]:
            if value is not None:
                words += ['-'+option, _number(value, minimum=0)]
        words.append(_select(ports, allowed=('ports', 'all_inputs')).to_sdc())
        return self._add(*words)

    def set_clock_uncertainty(self, uncertainty: float, clock: str, *, analysis: str = 'both') -> SDC:
        _choice(analysis, ('both', 'setup', 'hold'))
        return self._add('set_clock_uncertainty', *([] if analysis == 'both' else ['-'+analysis]),
                         _number(uncertainty, minimum=0), get_clocks(clock).to_sdc())

    def set_propagated_clock(self, clocks: Selection) -> SDC:
        return self._add('set_propagated_clock',
                         _select(clocks, default='clocks', allowed=('clocks',)).to_sdc())

    @staticmethod
    def _path(from_: Selection | None, to: Selection | None,
              through: Sequence[Selection] = ()) -> list[str]:
        words: list[str] = []
        for flag, selection in [('-from', from_), ('-to', to)]:
            if selection is not None:
                words += [flag, _select(selection).to_sdc()]
        # Each entry is an ordered stage; a get_pins([...]) is a union within a stage.
        if isinstance(through, (str, SdcCollection)):
            through = (through,)
        for selection in through:
            words += ['-through', _select(selection, default='pins',
                       allowed=('ports', 'pins')).to_sdc()]
        return words

    def set_false_path(self, *, from_: Selection | None = None, to: Selection | None = None,
                       through: Sequence[Selection] = (), analysis: str = 'both') -> SDC:
        _choice(analysis, ('both', 'setup', 'hold'))
        path = self._path(from_, to, through)
        if not path:
            raise ValueError('false path needs from_, to, or through')
        return self._add('set_false_path', *([] if analysis == 'both' else ['-'+analysis]), *path)

    def set_multicycle_path(self, cycles: int, *, from_: Selection | None = None,
                            to: Selection | None = None, analysis: str = 'setup',
                            reference: str | None = None) -> SDC:
        _choice(analysis, ('setup', 'hold'))
        if isinstance(cycles, bool) or not isinstance(cycles, int) or cycles < (analysis == 'setup'):
            raise ValueError('multicycle count must be an integer >= 1 for setup, >= 0 for hold')
        flags = [] if reference is None else ['-'+_choice(reference, ('start', 'end'))]
        return self._add('set_multicycle_path', str(cycles), '-'+analysis, *flags, *self._path(from_, to))

    def group_path(self, name: str, *, from_: Selection | None = None,
                   to: Selection | None = None, through: Sequence[Selection] = (),
                   weight: float | None = None) -> SDC:
        # Group labels may contain spaces (unlike netlist object names).
        if not isinstance(name, str) or not name.strip() or any(
            c in '{};"$\\#[]\r\n\t' or ord(c) < 32 for c in name
        ):
            raise ValueError('invalid path group name')
        words = ['group_path', '-name', '{'+name+'}', *self._path(from_, to, through)]
        if weight is not None:
            weight_text = _number(weight, minimum=0)
            if float(weight_text) > 100:
                raise ValueError('group weight must be in [0, 100]')
            words += ['-weight', weight_text]
        return self._add(*words)

    def set_max_delay(self, delay: float, *, from_: Selection | None = None,
                      to: Selection | None = None) -> SDC:
        return self._add('set_max_delay', _number(delay), *self._path(from_, to))

    def set_min_delay(self, delay: float, *, from_: Selection | None = None,
                      to: Selection | None = None) -> SDC:
        return self._add('set_min_delay', _number(delay), *self._path(from_, to))

    def set_case_analysis(self, value: int | str, pins: Selection) -> SDC:
        value = str(value)
        _choice(value, ('0', '1', 'rising', 'falling'))
        selection = _select(pins, default='pins', allowed=('ports', 'pins'))
        for name in selection.names:
            self._add('set_case_analysis', value, _collection(selection.kind, name).to_sdc())
        return self

    def set_timing_derate(self, value: float, *, analysis: str = 'both', target: str = 'data') -> SDC:
        _choice(analysis, ('both', 'early', 'late'))
        _choice(target, ('data', 'clock'))
        return self._add('set_timing_derate', *([] if analysis == 'both' else ['-'+analysis]),
                         '-'+target, _number(value, minimum=0))

    def set_max_transition(self, transition: float) -> SDC:
        return self._add('set_max_transition', _number(transition, minimum=0))

    def set_max_capacitance(self, capacitance: float) -> SDC:
        return self._add('set_max_capacitance', _number(capacitance, minimum=0))

    def set_max_fanout(self, fanout: float) -> SDC:
        return self._add('set_max_fanout', _number(fanout, minimum=0))
