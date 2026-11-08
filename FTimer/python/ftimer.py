#!/usr/bin/env python3
"""Small Python driver for the standalone ftimer executable.

The wrapper deliberately uses the CLI boundary instead of depending on a
particular compiler ABI.  It therefore works with an installed binary and is
also useful from regression scripts that compare ftimer with PrimeTime.
"""

from __future__ import annotations

import argparse
import bz2
import csv
import gzip
import math
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

from ftimer_sdc import SDC, SdcCollection, all_inputs, all_outputs, get_clocks, get_pins, get_ports


_QUERY_RE = re.compile(r"QUERY_PIN\s+name=(\S+)\s+found=(\d+)(.*)")
_KV_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
_STARTPOINT_RE = re.compile(r"^Startpoint:\s+(.+?)\s+\(")
_ENDPOINT_RE = re.compile(r"^Endpoint:\s+(.+?)\s+\(")
_SUMMARY_KV_RE = re.compile(r"([A-Za-z][A-Za-z0-9_]*)=([^\s]+)")
_SLACK_RE = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+|nan|inf|infinity))\s+"
    r"slack\s+\((?:MET|VIOLATED)\)\s*$", re.IGNORECASE)


def _number(value: str) -> float:
    """Parse ftimer's finite and non-finite floating point spellings."""
    value = value.strip().lower()
    if value in {"nan", "+nan", "-nan"}:
        return math.nan
    if value in {"inf", "+inf", "infinity", "+infinity"}:
        return math.inf
    if value in {"-inf", "-infinity"}:
        return -math.inf
    return float(value)


@dataclass(frozen=True)
class PinTiming:
    name: str
    found: bool
    values: Mapping[str, float]

    def __getitem__(self, key: str) -> float:
        return self.values[key]

    @property
    def arrival(self) -> Tuple[float, float]:
        return (self.values.get("max_rise_arrival", math.nan),
                self.values.get("max_fall_arrival", math.nan))

    @property
    def slew(self) -> Tuple[float, float]:
        return (self.values.get("max_rise_slew", math.nan),
                self.values.get("max_fall_slew", math.nan))


@dataclass(frozen=True)
class PinRecord:
    name: str
    rise_arrival: float
    fall_arrival: float
    rise_slew: float
    fall_slew: float


@dataclass(frozen=True)
class TimingPath:
    """Machine-readable summary of one OpenSTA-style reported path."""

    startpoint: str
    endpoint: str
    path_type: str
    slack: float
    text: str
    check_kind: str = "data"
    check_source: str = ""
    check_endpoint: str = ""
    path_group: str = ""
    path_based: bool = False
    cppr: float = 0.0


@dataclass(frozen=True)
class SiAggressor:
    net: str
    rise: bool = False
    offset_ns: float = 0.0
    driver_resistance_ohm: float = 0.0


@dataclass(frozen=True)
class SiNodeWaveform:
    node: int
    pin: str
    delay_delta_ns: float
    slew_delta_ns: float
    noise_peak_v: float
    noise_width_ns: float


@dataclass(frozen=True)
class SiWaveformResult:
    victim: str
    model: str
    active_aggressors: int
    samples: int
    nodes: Tuple[SiNodeWaveform, ...]
    waveform_file: Optional[str] = None


@dataclass(frozen=True)
class PowerSummary:
    frequency_hz: float
    activity: float
    leakage_w: float
    internal_w: float
    switching_w: float
    total_w: float


@dataclass(frozen=True)
class SwitchingActivity:
    """Both-edge transitions/second and the probability of logic one."""
    toggle_rate_hz: float
    static_probability: float = .5


@dataclass(frozen=True)
class InternalPowerActivity:
    """Conditioned input/output pin events; use related_pin='' for local input groups."""
    pin: str
    when: str
    related_pin: str
    toggle_rate_hz: float
    rise_ratio: float = .5


@dataclass(frozen=True)
class PowerDetail:
    summary: PowerSummary
    cells: Tuple[Mapping[str, object], ...]
    nets: Tuple[Mapping[str, object], ...]
    coverage: Mapping[str, int]


def read_saif(path: os.PathLike | str, *, strip_path: Optional[str] = None) -> Mapping[str, SwitchingActivity]:
    """Read hierarchical SAIF NET/PORT records in SI units.

    By default remove the outer INSTANCE (design top). For a testbench dump,
    pass strip_path='tb/dut'. Unknown-state time is excluded from P(1)'s
    denominator; TC still uses the full measured duration. No activity clamp.
    """
    raw = Path(path).read_text(encoding="utf-8")
    tokens = re.findall(r'"(?:\\.|[^"\\])*"|\(|\)|(?:\\.|[^\s()])+', raw)
    position = 0

    def parse(depth=0):
        nonlocal position
        if depth > 256 or position >= len(tokens):
            raise FTimerError("Malformed or excessively nested SAIF")
        token = tokens[position]
        position += 1
        if token != '(':
            if token == ')': raise FTimerError("Unexpected SAIF closing parenthesis")
            return token.strip('"')
        result = []
        while position < len(tokens) and tokens[position] != ')':
            result.append(parse(depth+1))
        if position >= len(tokens): raise FTimerError("Unclosed SAIF list")
        position += 1
        return result

    trees = []
    while position < len(tokens): trees.append(parse())
    if len(trees) != 1 or not isinstance(trees[0], list) or not trees[0] or trees[0][0] != 'SAIFILE':
        raise FTimerError("Expected one SAIFILE with TIMESCALE and DURATION")
    root = trees[0]
    metadata = {row[0]: row[1:] for row in root[1:] if isinstance(row, list) and row}
    try:
        scale, unit = metadata['TIMESCALE']
        seconds = float(scale) * {'s':1., 'ms':1e-3, 'us':1e-6, 'ns':1e-9, 'ps':1e-12, 'fs':1e-15}[unit.lower()]
        duration = float(metadata['DURATION'][0])
        if not math.isfinite(seconds*duration) or seconds <= 0 or duration <= 0: raise ValueError()
    except (KeyError, ValueError, IndexError):
        raise FTimerError("SAIF requires a positive DURATION and TIMESCALE (s/ms/us/ns/ps/fs)") from None
    explicit_scope = strip_path.strip('/') if strip_path is not None else None
    activities = {}

    def visit(node, hierarchy, default_scope=None):
        if not isinstance(node, list) or not node: return
        if node[0] == 'INSTANCE':
            if len(node) < 2 or not isinstance(node[1], str): raise FTimerError("Malformed SAIF INSTANCE")
            hierarchy = hierarchy + [node[1]]
            if default_scope is None: default_scope = '/'.join(hierarchy)
        if node[0] in ('NET', 'PORT'):
            entries = [node[1:]] if len(node)>1 and isinstance(node[1],str) else node[1:]
            for entry in entries:
                if not isinstance(entry, list) or not entry: continue
                fields = {r[0]:r[1] for r in entry[1:] if isinstance(r,list) and len(r)==2}
                if 'TC' not in fields: continue
                try:
                    tc, t0, t1 = (float(fields.get(key, 0)) for key in ('TC','T0','T1'))
                    if any(not math.isfinite(x) or x < 0 for x in (tc,t0,t1)) or t0+t1 > duration*(1+1e-6):
                        raise ValueError()
                except ValueError: raise FTimerError(f"Invalid SAIF activity for {entry[0]}") from None
                full = '/'.join(hierarchy+[entry[0]])
                full = re.sub(r'\\(.)', r'\1', full)
                scope = explicit_scope if explicit_scope is not None else default_scope
                if scope:
                    if not full.startswith(scope+'/'): continue
                    full = full[len(scope)+1:]
                record = SwitchingActivity(tc/(seconds*duration), t1/(t0+t1) if t0+t1 else .5)
                if full in activities and activities[full] != record:
                    raise FTimerError(f"Conflicting SAIF NET/PORT records for {full}")
                activities[full] = record
            return
        for child in node[1:]:
            if isinstance(child, list): visit(child, hierarchy, default_scope)

    visit(root, [])
    if not activities: raise FTimerError("No SAIF toggle records matched the requested scope")
    return activities


def read_vcd(path: os.PathLike | str, *, strip_path: Optional[str] = None,
             start_ns: float = 0., end_ns: Optional[float] = None) -> Mapping[str, SwitchingActivity]:
    """Stream digital VCD into per-bit averaged activities, without storing events.

    Count known 0<->1 events in [start, end) for an explicit end, matching
    PrimeTime's VCD windows. With no end, include the last dump timestamp.
    Initialization and transitions to/from X/Z do not count.
    P(1) excludes X/Z dwell, as in read_saif. Default end is the last timestamp;
    an explicit window must lie within the dump. This is averaged power input,
    not a time-based power/glitch or correlated-state simulation.
    """
    if (not math.isfinite(start_ns) or start_ns < 0 or
        (end_ns is not None and (not math.isfinite(end_ns) or end_ns <= start_ns))):
        raise FTimerError("VCD requires a finite nonnegative start and end > start (ns)")
    # Each identifier has one state/counter vector, shared by all its aliases.
    signals, scopes = {}, []
    default_scope = None
    explicit_scope = strip_path.strip('/') if strip_path is not None else None
    scale_ns = None
    now = 0
    start = end = None

    def next_token(tokens):
        try: return next(tokens)
        except StopIteration: raise FTimerError("Unexpected end of VCD") from None

    def directive(tokens):
        words = []
        while True:
            word = next_token(tokens)
            if word == '$end': return words
            words.append(word)

    def integrate(signal, until):
        dt = max(0., min(until, end) - max(signal['time'], start))
        if dt:
            for bit, value in enumerate(signal['state']):
                if value in '01': signal['known'][bit] += dt
                if value == '1': signal['ones'][bit] += dt
        signal['time'] = until

    vcd_path = Path(path)
    opener = {'.gz':gzip.open,'.bz2':bz2.open}.get(vcd_path.suffix.lower(),open)
    with opener(vcd_path, mode='rt', encoding='utf-8') as stream:
        tokens = (token for line in stream for token in line.split())
        for token in tokens:
            if token == '$enddefinitions':
                if directive(tokens): raise FTimerError("Malformed VCD enddefinitions")
                break
            if not token.startswith('$'): raise FTimerError("Expected VCD header directive")
            fields = directive(tokens)
            if token == '$timescale':
                matched = re.fullmatch(r'(1|10|100)(s|ms|us|ns|ps|fs)', ''.join(fields), re.IGNORECASE)
                if not matched or scale_ns is not None: raise FTimerError("Invalid or duplicate VCD timescale")
                scale_ns = int(matched[1])*{'s':1e9,'ms':1e6,'us':1e3,'ns':1.,'ps':1e-3,'fs':1e-6}[matched[2].lower()]
            elif token == '$scope':
                if len(fields)!=2: raise FTimerError("Malformed VCD scope")
                scopes.append(fields[1].lstrip('\\'))
                if default_scope is None: default_scope = '/'.join(scopes)
            elif token == '$upscope':
                if fields or not scopes: raise FTimerError("Unbalanced VCD upscope")
                scopes.pop()
            elif token == '$var':
                if len(fields)<4: raise FTimerError("Malformed VCD variable")
                kind, width_text, code, reference, *suffix = fields
                # Real/string/event records have no binary dwell-time meaning.
                if kind in ('real','realtime','string','event'): continue
                try: width = int(width_text)
                except ValueError: raise FTimerError("Invalid VCD variable width") from None
                if width <= 0: raise FTimerError("Invalid VCD variable width")
                full = '/'.join(scopes+[reference.lstrip('\\')])
                scope = explicit_scope if explicit_scope is not None else default_scope
                if scope:
                    if not full.startswith(scope+'/'): continue
                    full = full[len(scope)+1:]
                indices = None
                if suffix:
                    match = re.fullmatch(r'\[(-?\d+)(?::(-?\d+))?\]', ''.join(suffix))
                    if not match: raise FTimerError(f"Invalid VCD range for {full}")
                    left = int(match[1]); right = int(match[2] if match[2] is not None else match[1])
                    step = 1 if right>=left else -1
                    if abs(right-left)+1 != width: raise FTimerError(f"VCD width/range mismatch for {full}")
                    indices = range(left,right+step,step)
                if width>1 and indices is None: indices = range(width-1,-1,-1)
                names = [full+f'[{i}]' for i in indices] if indices is not None else [full]
                if code in signals:
                    if signals[code]['width']!=width: raise FTimerError("Conflicting VCD alias widths")
                    signals[code]['aliases'].append(names)
                else:
                    signals[code] = dict(width=width, aliases=[names], state='x'*width,
                                         time=0, known=[0.]*width, ones=[0.]*width, toggles=[0]*width)
        else: raise FTimerError("VCD is missing enddefinitions")
        if scale_ns is None: raise FTimerError("VCD is missing timescale")
        if not signals: raise FTimerError("No digital VCD variables matched the requested scope")
        start = start_ns/scale_ns
        end = end_ns/scale_ns if end_ns is not None else math.inf
        for token in tokens:
            if token.startswith('#'):
                try: timestamp = int(token[1:])
                except ValueError: raise FTimerError("Invalid VCD timestamp") from None
                if timestamp < now: raise FTimerError("VCD timestamps must be nondecreasing")
                now = timestamp
                continue
            if token in ('$dumpvars','$dumpall','$dumpon','$dumpoff','$end'): continue
            if token.startswith('$'):
                directive(tokens)
                continue
            if token[0] in 'bBrRsS':
                value, code = token[1:].lower(), next_token(tokens)
                if token[0] in 'rRsS': continue
                if not value or any(c not in '01xz' for c in value): raise FTimerError("Invalid VCD vector value")
            elif token[0] in '01xXzZ':
                value, code = token[0].lower(), token[1:]
                if not code: raise FTimerError("Missing VCD scalar identifier")
            else: raise FTimerError(f"Unsupported VCD value token {token!r}")
            signal = signals.get(code)
            if signal is None: continue  # An unselected scope or non-digital variable.
            if len(value)>signal['width']: raise FTimerError("VCD value exceeds declared width")
            value = value.rjust(signal['width'], value[0] if value[0] in 'xz' else '0')
            integrate(signal, now)
            if start <= now and (end_ns is None or now < end):
                for bit, (old,new) in enumerate(zip(signal['state'],value)):
                    if old in '01' and new in '01' and old!=new: signal['toggles'][bit] += 1
            signal['state'] = value
    if start >= now or (end_ns is not None and end > now+1e-9):
        raise FTimerError("VCD analysis window must have positive duration within the dump")
    end = min(end,now)
    duration_s = (end-start)*scale_ns*1e-9
    activities = {}
    for signal in signals.values():
        integrate(signal,now)
        for names in signal['aliases']:
            for bit, name in enumerate(names):
                record = SwitchingActivity(signal['toggles'][bit]/duration_s,
                    signal['ones'][bit]/signal['known'][bit] if signal['known'][bit] else .5)
                if name in activities and activities[name]!=record: raise FTimerError(f"Conflicting VCD records for {name}")
                activities[name] = record
    return activities


@dataclass(frozen=True)
class SiSummary:
    victim_nets: int
    total_coupling_cap: float
    max_victim_coupling_cap: float
    crosstalk_waveform_solver: bool
    si_timing_applied: bool = False


@dataclass(frozen=True)
class SiCoupling:
    victim_net: str
    aggressor_net: str
    coupling_cap: float
    victim_total_coupling_cap: float
    coupling_ratio: float


@dataclass(frozen=True)
class DesignRuleLimits:
    max_fanout: float
    max_capacitance: float
    max_transition: float


@dataclass(frozen=True)
class DesignRuleViolation:
    rule: str
    object: str
    limit: float
    value: float


@dataclass(frozen=True)
class TimingCheckCoverage:
    pin: str
    arc: int
    transition: str
    analysis: str
    kind: str
    state: str


@dataclass(frozen=True)
class ScenarioTiming:
    """Timing result for one MCMM scenario.

    A scenario may select its own Liberty/SPEF/SDC and PVT while sharing the
    same netlist.  Slack values are in ns; ``paths`` contains the requested
    structured reports for that scenario.
    """

    name: str
    voltage: float
    temperature: float
    worst_setup_slack: float
    worst_hold_slack: float
    paths: Tuple[TimingPath, ...]


class FTimerError(RuntimeError):
    """Raised when the ftimer process cannot complete an analysis."""


class FTimer:
    """Run ftimer with a PrimeTime-like, script friendly interface.

    Inputs are accepted as paths or path-like strings.  ``liberty``,
    ``verilog``, ``spef`` and ``sdc`` may each be one path or an iterable of
    paths. ``constraints=SDC()`` adds Python-defined constraints after the file
    inputs. The command is assembled on every call, so a single object can be
    used for several report/query passes without stale process state.
    """

    def __init__(
        self,
        *,
        executable: Optional[os.PathLike | str] = None,
        liberty: Sequence[os.PathLike | str] | os.PathLike | str = (),
        verilog: Sequence[os.PathLike | str] | os.PathLike | str = (),
        spef: Sequence[os.PathLike | str] | os.PathLike | str = (),
        sdc: Sequence[os.PathLike | str] | os.PathLike | str = (),
        constraints: Optional[SDC] = None,
        top: Optional[str] = None,
        threads: int = 1,
        voltage: float = 1.0,
        temperature: float = 25.0,
        env: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.executable = Path(executable) if executable else self._default_executable()
        self.liberty = self._paths(liberty)
        self.verilog = self._paths(verilog)
        self.spef = self._paths(spef)
        self.sdc = self._paths(sdc)
        if constraints is not None and not isinstance(constraints, SDC):
            raise TypeError('constraints must be an SDC object')
        self.constraints = constraints if constraints is not None else SDC()
        self.top = top
        self.threads = int(threads)
        self.voltage = float(voltage)
        self.temperature = float(temperature)
        self.env = dict(env or {})

    @staticmethod
    def _paths(value: Sequence[os.PathLike | str] | os.PathLike | str) -> Tuple[str, ...]:
        if isinstance(value, (str, os.PathLike)):
            return (os.fspath(value),)
        return tuple(os.fspath(item) for item in value)

    @staticmethod
    def _default_executable() -> Path:
        override = os.environ.get("FTIMER_BIN")
        if override:
            return Path(override)
        root = Path(__file__).resolve().parents[1]
        candidates = (
            root / "bin" / "ftimer",
            root / "bin" / "time_engine_cli",
            root / "build" / "bin" / "time_engine_cli",
            root / "build" / "bin" / "time_engine_cli.exe",
            root / "build_standalone" / "bin" / "time_engine_cli",
            root / "build_standalone" / "bin" / "time_engine_cli.exe",
        )
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def write_sdc(self, path: os.PathLike | str) -> Path:
        """Export file constraints followed by Python constraints as one SDC.

        The engine treats each read_sdc as a complete constraint state, so
        combining the inputs also preserves clocks across multiple files.
        Python values use ns/pF independently of preceding file units.
        """
        contents = [Path(name).read_text(encoding='utf-8') for name in self.sdc]
        if self.constraints:
            contents.append(self.constraints.to_sdc())
        path = Path(path)
        path.write_text('\n'.join(contents) + '\n', encoding='utf-8')
        return path

    def command(self, *extra: str, dump_pins: bool = False,
                report: int = 0, report_min: int = 0,
                report_reg2reg: int = 0, report_check: int = 0,
                report_check_min: int = 0, report_format: str = "default",
                group: Optional[str] = None,
                pba_mode: str = "none", pba_limit: int = 1000000,
                verbose: bool = False,
                sdc_path: Optional[os.PathLike | str] = None) -> list[str]:
        """Build argv; export Python constraints with write_sdc and pass sdc_path.

        run() and all query/report methods materialize constraints automatically.
        """
        if sdc_path is None and (self.constraints or len(self.sdc) > 1):
            raise ValueError('use run(), or write_sdc(path) and command(sdc_path=path) for combined constraints')
        cmd = [os.fspath(self.executable)]
        for path in self.liberty:
            cmd += ["-lib", path]
        for path in self.verilog:
            cmd += ["-verilog", path]
        if self.top:
            cmd += ["-top", self.top]
        for path in self.spef:
            cmd += ["-spef", path]
        for path in ((os.fspath(sdc_path),) if sdc_path is not None else self.sdc):
            cmd += ["-sdc", path]
        cmd += ["-threads", str(self.threads), "-voltage", str(self.voltage),
                "-temperature", str(self.temperature)]
        if dump_pins:
            cmd.append("-dump_pins")
        if report:
            cmd += ["-report", str(int(report))]
        if report_min:
            cmd += ["-report_min", str(int(report_min))]
        if report_reg2reg:
            cmd += ["-report_reg2reg", str(int(report_reg2reg))]
        if report_check:
            cmd += ["-report_check", str(int(report_check))]
        if report_check_min:
            cmd += ["-report_check_min", str(int(report_check_min))]
        if report_format:
            cmd += ["-report_format", report_format]
        if group is not None:
            cmd += ["-group", group]
        if pba_mode not in ("none", "exhaustive"):
            raise ValueError("pba_mode must be none or exhaustive")
        if pba_mode != "none":
            cmd += ["-pba_mode", pba_mode, "-pba_limit", str(pba_limit)]
        if verbose:
            cmd.append("-verbose")
        cmd.extend(extra)
        return cmd

    def run(self, *extra: str, check: bool = True, timeout: Optional[float] = None,
            **options: object) -> subprocess.CompletedProcess[str]:
        if (self.constraints or len(self.sdc) > 1) and options.get('sdc_path') is None:
            with tempfile.TemporaryDirectory(prefix='ftimer_constraints_') as directory:
                path = self.write_sdc(Path(directory) / 'constraints.sdc')
                options['sdc_path'] = path
                return self._run(*extra, check=check, timeout=timeout, **options)
        return self._run(*extra, check=check, timeout=timeout, **options)

    def _run(self, *extra: str, check: bool, timeout: Optional[float],
             **options: object) -> subprocess.CompletedProcess[str]:
        command = self.command(*extra, **options)
        env = os.environ.copy()
        env.update(self.env)
        try:
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env,
                                    timeout=timeout, check=False)
        except OSError as exc:
            raise FTimerError(f"cannot execute ftimer: {command[0]}: {exc}") from exc
        if check and result.returncode:
            raise FTimerError(f"ftimer exited with {result.returncode}\n{result.stdout}")
        return result

    def query_pin(self, name: str, *, timeout: Optional[float] = None) -> PinTiming:
        result = self.run("-query_pin", name, timeout=timeout)
        for line in result.stdout.splitlines():
            match = _QUERY_RE.search(line)
            if not match or match.group(1) != name:
                continue
            found = match.group(2) == "1"
            values: Dict[str, float] = {}
            for key, value in _KV_RE.findall(match.group(3)):
                values[key] = _number(value)
            return PinTiming(name=name, found=found, values=values)
        raise FTimerError(f"ftimer did not return QUERY_PIN for {name!r}\n{result.stdout}")

    def dump_pins(self, *, timeout: Optional[float] = None) -> Dict[str, PinRecord]:
        result = self.run(dump_pins=True, timeout=timeout)
        lines = result.stdout.splitlines()
        try:
            start = lines.index("pin_name,rise_arrival,fall_arrival,rise_slew,fall_slew") + 1
        except ValueError as exc:
            raise FTimerError("ftimer output does not contain a pin dump") from exc
        records: Dict[str, PinRecord] = {}
        for row in csv.reader(lines[start:]):
            if len(row) != 5 or not row[0]:
                continue
            records[row[0]] = PinRecord(row[0], *(_number(v) for v in row[1:]))
        return records

    def report_timing(self, *, max_paths: int = 0, min_paths: int = 0,
                      reg2reg: int = 0, report_format: str = "opensta",
                      group: Optional[str] = None,
                      pba_mode: str = "none", pba_limit: int = 1000000,
                      timeout: Optional[float] = None) -> str:
        return self.run(report=max_paths, report_min=min_paths,
                        report_reg2reg=reg2reg, report_format=report_format,
                        group=group,
                        pba_mode=pba_mode, pba_limit=pba_limit,
                        timeout=timeout).stdout

    def analyze_scenarios(
        self,
        scenarios: Mapping[str, Mapping[str, object]],
        *,
        max_paths: int = 1,
        min_paths: int = 1,
        report_format: str = "opensta",
        timeout: Optional[float] = None,
    ) -> Dict[str, ScenarioTiming]:
        """Run a small MCMM sweep and return one result per scenario.

        Each value may override ``liberty``, ``spef``, ``sdc``, ``verilog``,
        ``top``, ``threads``, ``voltage`` or ``temperature``.  The method
        deliberately runs scenarios independently so a corner cannot leak
        state into another corner; callers can select the worst setup/hold
        result with normal Python ordering.
        """
        results: Dict[str, ScenarioTiming] = {}
        base = {
            "liberty": self.liberty,
            "verilog": self.verilog,
            "spef": self.spef,
            "sdc": self.sdc,
            "constraints": self.constraints,
            "top": self.top,
            "threads": self.threads,
            "voltage": self.voltage,
            "temperature": self.temperature,
            "env": self.env,
            "executable": self.executable,
        }
        for name, overrides in scenarios.items():
            config = dict(base)
            config.update(overrides)
            timer = FTimer(**config)
            paths = tuple(timer.report_paths(
                max_paths=max_paths,
                min_paths=min_paths,
                report_format=report_format,
                timeout=timeout,
            ))
            # Normal data reports use Path Type (max/min) to distinguish
            # setup and hold.  Timing-check reports use check_kind.  Keep
            # both conventions so MCMM results remain correct for either
            # report source.
            setup = [p.slack for p in paths if
                     p.path_type == "max" or p.check_kind in {"setup", "recovery", "output_delay"}]
            hold = [p.slack for p in paths if
                    p.path_type == "min" or p.check_kind in {"hold", "removal"}]
            results[str(name)] = ScenarioTiming(
                name=str(name),
                voltage=timer.voltage,
                temperature=timer.temperature,
                worst_setup_slack=min(setup, default=math.nan),
                worst_hold_slack=min(hold, default=math.nan),
                paths=paths,
            )
        return results

    def report_paths(self, *, max_paths: int = 0, min_paths: int = 0,
                     reg2reg: int = 0, report_format: str = "opensta",
                     group: Optional[str] = None,
                     pba_mode: str = "none", pba_limit: int = 1000000,
                     timeout: Optional[float] = None) -> Tuple[TimingPath, ...]:
        """Return summaries while retaining the original report text per path."""
        text = self.report_timing(max_paths=max_paths, min_paths=min_paths,
                                  reg2reg=reg2reg, report_format=report_format,
                                  group=group,
                                  pba_mode=pba_mode, pba_limit=pba_limit,
                                  timeout=timeout)
        result = []
        # A report may contain blank lines between its header and summary, so
        # split on the next Startpoint marker rather than on blank lines.
        blocks = re.split(r"(?=^Startpoint:\s+)", text, flags=re.MULTILINE)
        for block in blocks:
            start = endpoint = path_type = None
            check_kind = "data"
            check_source = check_endpoint_name = ""
            path_group = ""
            path_based, cppr = False, 0.0
            slack = math.nan
            for line in block.splitlines():
                match = _STARTPOINT_RE.match(line)
                if match:
                    start = match.group(1).strip()
                match = _ENDPOINT_RE.match(line)
                if match:
                    endpoint = match.group(1).strip()
                if line.startswith("Path Type:"):
                    path_type = line.split(":", 1)[1].strip()
                if line.startswith("Path Group:"):
                    path_group = line.split(":", 1)[1].strip()
                if line.startswith("Path Analysis:"):
                    path_based = line.split(":", 1)[1].strip() == "pba_exhaustive"
                if line.startswith("Clock Pessimism Removal:"):
                    cppr = _number(line.split(":", 1)[1].strip())
                if line.startswith("TimingCheck:"):
                    check_kind = line.split(":", 1)[1].strip()
                if line.startswith("DataCheckFrom:"):
                    check_source = line.split(":", 1)[1].strip()
                if line.startswith("DataCheckTo:"):
                    check_endpoint_name = line.split(":", 1)[1].strip()
                match = _SLACK_RE.match(line)
                if match:
                    slack = _number(match.group(1))
            if start and endpoint and path_type:
                result.append(TimingPath(start, endpoint, path_type, slack, block,
                                         check_kind, check_source, check_endpoint_name, path_group, path_based, cppr))
        return tuple(result)

    def report_check_paths(self, *, max_paths: int = 0, min_paths: int = 0,
                           report_format: str = "opensta",
                           group: Optional[str] = None,
                           pba_mode: str = "none", pba_limit: int = 1000000,
                           timeout: Optional[float] = None) -> Tuple[TimingPath, ...]:
        text = self.run(report_check=max_paths, report_check_min=min_paths,
                        report_format=report_format, group=group, pba_mode=pba_mode,
                        pba_limit=pba_limit, timeout=timeout).stdout
        blocks = re.split(r"(?=^Startpoint:\s+)", text, flags=re.MULTILINE)
        result = []
        for block in blocks:
            start = endpoint = path_type = None
            check_kind = "data"
            check_source = check_endpoint_name = ""
            path_group = ""
            path_based, cppr = False, 0.0
            slack = math.nan
            for line in block.splitlines():
                match = _STARTPOINT_RE.match(line)
                if match: start = match.group(1).strip()
                match = _ENDPOINT_RE.match(line)
                if match: endpoint = match.group(1).strip()
                if line.startswith("Path Type:"):
                    path_type = line.split(":", 1)[1].strip()
                if line.startswith("Path Group:"):
                    path_group = line.split(":", 1)[1].strip()
                if line.startswith("Path Analysis:"):
                    path_based = line.split(":", 1)[1].strip() == "pba_exhaustive"
                if line.startswith("Clock Pessimism Removal:"):
                    cppr = _number(line.split(":", 1)[1].strip())
                if line.startswith("TimingCheck:"):
                    check_kind = line.split(":", 1)[1].strip()
                if line.startswith("DataCheckFrom:"):
                    check_source = line.split(":", 1)[1].strip()
                if line.startswith("DataCheckTo:"):
                    check_endpoint_name = line.split(":", 1)[1].strip()
                match = _SLACK_RE.match(line)
                if match: slack = _number(match.group(1))
            if start and endpoint and path_type:
                result.append(TimingPath(start, endpoint, path_type, slack, block,
                                         check_kind, check_source, check_endpoint_name, path_group, path_based, cppr))
        return tuple(result)

    def estimate_power(self, frequency_hz: float, activity: float = 0.1,
                       *, activities: Optional[Mapping[str, SwitchingActivity]] = None,
                       internal_activities: Sequence[InternalPowerActivity] = (),
                       propagation: str = 'clocked',
                       timeout: Optional[float] = None) -> PowerSummary:
        return self.estimate_power_detail(frequency_hz, activity, activities=activities,
            internal_activities=internal_activities, propagation=propagation, timeout=timeout).summary

    def estimate_power_detail(self, frequency_hz: float, activity: float = 0.1,
                       *, activities: Optional[Mapping[str, SwitchingActivity]] = None,
                       internal_activities: Sequence[InternalPowerActivity] = (),
                       propagation: str = 'clocked',
                       timeout: Optional[float] = None) -> PowerDetail:
        if propagation not in ('clocked','independent'):
            raise FTimerError('Power propagation must be clocked or independent')
        extra = ['-power_detail','-power_propagation',propagation]
        rows = []
        for name, value in (activities or {}).items():
            if (not math.isfinite(value.toggle_rate_hz) or value.toggle_rate_hz < 0 or
                not math.isfinite(value.static_probability) or not 0 <= value.static_probability <= 1):
                raise FTimerError(f"Invalid switching activity for {name}")
            if any(c in name for c in '\t\r\n'): raise FTimerError("Invalid activity object name")
            rows.append(f'{name}\t{value.toggle_rate_hz}\t{value.static_probability}\n')
        internal_rows=[]
        for value in internal_activities:
            if (not math.isfinite(value.toggle_rate_hz) or value.toggle_rate_hz<0 or
                not math.isfinite(value.rise_ratio) or not 0<=value.rise_ratio<=1):
                raise FTimerError(f"Invalid internal power activity for {value.pin}")
            if any(c in field for field in (value.pin,value.when,value.related_pin) for c in '\t\r\n'):
                raise FTimerError("Invalid internal power activity field")
            internal_rows.append(f'{value.pin}\t{value.when}\t{value.related_pin}\t{value.toggle_rate_hz}\t{value.rise_ratio}\n')
        with tempfile.TemporaryDirectory(prefix='ftimer_activity_') as directory:
            if rows:
                path = Path(directory)/'activity.tsv'
                path.write_text(''.join(rows), encoding='utf-8')
                extra.extend(['-power_activity_file', str(path)])
            if internal_rows:
                path=Path(directory)/'internal_activity.tsv'
                path.write_text(''.join(internal_rows),encoding='utf-8')
                extra.extend(['-power_internal_activity_file',str(path)])
            result = self.run("-power", str(float(frequency_hz)), "-activity", str(float(activity)),
                              *extra, timeout=timeout)
        cells, nets, coverage = [], [], {}
        summary = None
        for line in result.stdout.splitlines():
            if line.startswith('POWER_CELL ') or line.startswith('POWER_NET '):
                values = dict(_SUMMARY_KV_RE.findall(line))
                for key in set(values)-{'name','source'}: values[key] = _number(values[key])
                (cells if line.startswith('POWER_CELL ') else nets).append(values)
            if line.startswith('POWER_COVERAGE '):
                coverage = {key:int(value) for key,value in _SUMMARY_KV_RE.findall(line)}
            if not line.startswith("POWER_SUMMARY "): continue
            values = {key: _number(value) for key, value in _SUMMARY_KV_RE.findall(line)}
            summary = PowerSummary(
                frequency_hz=values["frequency_hz"], activity=values["activity"],
                leakage_w=values["leakage_w"], internal_w=values["internal_w"],
                switching_w=values["switching_w"], total_w=values["total_w"])
        if summary is not None: return PowerDetail(summary, tuple(cells), tuple(nets), coverage)
        raise FTimerError("ftimer did not return POWER_SUMMARY\n" + result.stdout)

    def estimate_power_saif(self, saif: os.PathLike | str, frequency_hz: float,
                            *, strip_path: Optional[str] = None, default_activity: float = 0.,
                            propagation: str = 'clocked',
                            timeout: Optional[float] = None) -> PowerSummary:
        return self.estimate_power(frequency_hz, default_activity,
            activities=read_saif(saif, strip_path=strip_path), propagation=propagation, timeout=timeout)

    def estimate_power_vcd(self, vcd: os.PathLike | str, frequency_hz: float,
                           *, strip_path: Optional[str] = None, start_ns: float = 0.,
                           end_ns: Optional[float] = None, default_activity: float = 0.,
                           propagation: str = 'clocked',
                           timeout: Optional[float] = None) -> PowerSummary:
        return self.estimate_power(frequency_hz, default_activity,
            activities=read_vcd(vcd, strip_path=strip_path, start_ns=start_ns, end_ns=end_ns), propagation=propagation, timeout=timeout)

    def analyze_si(self, *, timeout: Optional[float] = None) -> SiSummary:
        result = self.run("-si", timeout=timeout)
        for line in result.stdout.splitlines():
            if not line.startswith("SI_SUMMARY "):
                continue
            values = {key: _number(value) for key, value in _SUMMARY_KV_RE.findall(line)}
            return SiSummary(
                victim_nets=int(values["victim_nets"]),
                total_coupling_cap=values["total_coupling_cap"],
                max_victim_coupling_cap=values["max_victim_coupling_cap"],
                crosstalk_waveform_solver=bool(values["crosstalk_waveform_solver"]),
                si_timing_applied=bool(values.get("si_timing_applied",0)),)
        raise FTimerError("ftimer did not return SI_SUMMARY\n" + result.stdout)

    def analyze_si_detail(self, *, timeout: Optional[float] = None) -> Tuple[SiCoupling, ...]:
        result = self.run("-si_detail", timeout=timeout)
        records = []
        for line in result.stdout.splitlines():
            if not line.startswith("SI_COUPLING "):
                continue
            values = dict(_SUMMARY_KV_RE.findall(line))
            if not {"victim", "aggressor", "cap", "victim_total", "ratio"} <= values.keys():
                continue
            records.append(SiCoupling(
                victim_net=values["victim"],
                aggressor_net=values["aggressor"],
                coupling_cap=_number(values["cap"]),
                victim_total_coupling_cap=_number(values["victim_total"]),
                coupling_ratio=_number(values["ratio"]),
            ))
        return tuple(records)

    def solve_si_waveforms(self, victim: str, aggressors: Sequence[SiAggressor], *,
                           victim_rise: bool = True, quiet_victim: bool = False,
                           respect_timing_windows: bool = True, victim_resistance_ohm: float = 0.0,
                           step_ns: float = 0.0005, waveform_file: Optional[os.PathLike | str] = None,
                           timeout: Optional[float] = None) -> SiWaveformResult:
        """Solve linear Thevenin coupled RC; optionally export baseline/coupled CSV."""
        extra = ["-si_victim", victim, "-si_victim_r", str(victim_resistance_ohm), "-si_step", str(step_ns)]
        for a in aggressors:
            extra += ["-si_aggressor", a.net, "rise" if a.rise else "fall", str(a.offset_ns), str(a.driver_resistance_ohm)]
        if not victim_rise:
            extra.append("-si_fall")
        if quiet_victim:
            extra.append("-si_quiet")
        if not respect_timing_windows:
            extra.append("-si_no_windows")
        if waveform_file is not None:
            extra += ["-si_waveform_file", os.fspath(waveform_file)]
        output = self.run(*extra, timeout=timeout).stdout
        header = None
        nodes = []
        for line in output.splitlines():
            values = dict(_SUMMARY_KV_RE.findall(line))
            if line.startswith("SI_WAVEFORM "):
                header = values
            elif line.startswith("SI_NODE "):
                nodes.append(SiNodeWaveform(int(values["node"]), values["pin"],
                    *(_number(values[key]) for key in ("delay_delta_ns", "slew_delta_ns", "noise_peak_v", "noise_width_ns"))))
        if header is None:
            raise RuntimeError("CLI did not return an SI waveform result")
        return SiWaveformResult(header["victim"], header["model"], int(header["active_aggressors"]),
            int(header["samples"]), tuple(nodes), None if waveform_file is None else os.fspath(waveform_file))

    def timing_check_coverage(self, *, timeout: Optional[float] = None) -> Tuple[TimingCheckCoverage, ...]:
        result = self.run("-check_coverage", timeout=timeout)
        records = []
        for line in result.stdout.splitlines():
            if not line.startswith("TIMING_CHECK_COVERAGE "):
                continue
            values = {key: value for key, value in _SUMMARY_KV_RE.findall(line)}
            records.append(TimingCheckCoverage(
                pin=values.get("pin", ""), arc=int(values.get("arc", "-1")),
                transition=values.get("transition", ""),
                analysis=values.get("analysis", ""),
                kind=values.get("kind", ""), state=values.get("state", "")))
        return tuple(records)

    def design_rule_limits(self, *, timeout: Optional[float] = None) -> DesignRuleLimits:
        result = self.run("-design_rules", timeout=timeout)
        for line in result.stdout.splitlines():
            if line.startswith("DESIGN_RULES "):
                values = {key: _number(value) for key, value in _SUMMARY_KV_RE.findall(line)}
                return DesignRuleLimits(
                    values.get("max_fanout", -1.0),
                    values.get("max_capacitance", -1.0),
                    values.get("max_transition", -1.0))
        raise RuntimeError("time_engine_cli did not emit DESIGN_RULES")

    def design_rule_violations(self, *, timeout: Optional[float] = None) -> Tuple[DesignRuleViolation, ...]:
        result = self.run("-design_rule_violations", timeout=timeout)
        records = []
        for line in result.stdout.splitlines():
            if not line.startswith("DESIGN_RULE_VIOLATION "):
                continue
            values = {key: value for key, value in _SUMMARY_KV_RE.findall(line)}
            records.append(DesignRuleViolation(
                values.get("rule", ""), values.get("object", ""),
                _number(values.get("limit", "nan")),
                _number(values.get("value", "nan"))))
        return tuple(records)


def _main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", dest="executable")
    parser.add_argument("--liberty", "--lib", action="append", default=[])
    parser.add_argument("--verilog", action="append", default=[])
    parser.add_argument("--spef", action="append", default=[])
    parser.add_argument("--sdc", action="append", default=[])
    parser.add_argument("--top")
    parser.add_argument("--query-pin", action="append", default=[])
    parser.add_argument("--dump-pins", action="store_true")
    parser.add_argument("--report", type=int, default=0)
    parser.add_argument("--report-min", type=int, default=0)
    parser.add_argument("--group", help="restrict reports to an explicit SDC path group")
    parser.add_argument("--pba-mode", choices=("none", "exhaustive"), default="none")
    parser.add_argument("--power", type=float, metavar="HZ")
    parser.add_argument("--activity", type=float, default=0.1)
    activity_input = parser.add_mutually_exclusive_group()
    activity_input.add_argument("--saif", help="SAIF with TIMESCALE/DURATION and per-node activity")
    activity_input.add_argument("--vcd", help="digital VCD, reduced to per-bit averaged activities")
    parser.add_argument("--saif-strip-path", help="testbench scope, e.g. tb/dut")
    parser.add_argument("--vcd-strip-path", help="VCD testbench scope, e.g. tb/dut")
    parser.add_argument("--vcd-start-ns", type=float, default=0.)
    parser.add_argument("--vcd-end-ns", type=float)
    parser.add_argument("--power-detail", action="store_true")
    parser.add_argument("--power-propagation", choices=('clocked','independent'), default='clocked')
    parser.add_argument("--si", action="store_true")
    parser.add_argument("--si-detail", action="store_true")
    parser.add_argument("--check-coverage", action="store_true")
    parser.add_argument("--design-rules", action="store_true")
    parser.add_argument("--design-rule-violations", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit query/dump results as JSON")
    args = parser.parse_args(argv)
    if (args.saif or args.vcd) and args.power is None:
        parser.error("--saif/--vcd requires --power HZ")
    timer = FTimer(executable=args.executable, liberty=args.liberty,
                   verilog=args.verilog, spef=args.spef, sdc=args.sdc, top=args.top)
    def power_result():
        annotations=read_saif(args.saif,strip_path=args.saif_strip_path) if args.saif else None
        if args.vcd:
            annotations=read_vcd(args.vcd,strip_path=args.vcd_strip_path,
                                 start_ns=args.vcd_start_ns,end_ns=args.vcd_end_ns)
        return timer.estimate_power_detail(args.power,0. if annotations is not None else args.activity,
                                           activities=annotations,propagation=args.power_propagation)
    if args.json:
        import json
        output: dict[str, object] = {}
        if args.query_pin:
            pins = {}
            for name in args.query_pin:
                timing = timer.query_pin(name)
                pins[name] = dict(timing.values) | {"found": timing.found}
            output["pins"] = pins
        if args.dump_pins:
            output["dump"] = {name: record.__dict__ for name, record in timer.dump_pins().items()}
        if args.report or args.report_min:
            output["report"] = timer.report_timing(max_paths=args.report,
                                                    min_paths=args.report_min, group=args.group, pba_mode=args.pba_mode)
        if args.power is not None:
            detail=power_result()
            output["power"] = detail.summary.__dict__
            if args.power_detail:
                output["power_detail"] = {'cells':detail.cells,'nets':detail.nets,'coverage':detail.coverage}
        if args.si:
            output["si"] = timer.analyze_si().__dict__
        if args.si_detail:
            output["si_detail"] = [item.__dict__ for item in timer.analyze_si_detail()]
        if args.check_coverage:
            output["timing_check_coverage"] = [item.__dict__
                                                for item in timer.timing_check_coverage()]
        if args.design_rules:
            output["design_rules"] = timer.design_rule_limits().__dict__
        if args.design_rule_violations:
            output["design_rule_violations"] = [item.__dict__ for item in timer.design_rule_violations()]
        print(json.dumps(output, allow_nan=True, indent=2))
        return 0
    for name in args.query_pin:
        print(timer.query_pin(name))
    if args.dump_pins:
        for record in timer.dump_pins().values():
            print(record)
    if args.report or args.report_min:
        print(timer.report_timing(max_paths=args.report, min_paths=args.report_min, group=args.group, pba_mode=args.pba_mode))
    if args.power is not None:
        detail=power_result()
        print(detail if args.power_detail else detail.summary)
    if args.si:
        print(timer.analyze_si())
    if args.si_detail:
        for item in timer.analyze_si_detail():
            print(item)
    if args.check_coverage:
        for item in timer.timing_check_coverage():
            print(item)
    if args.design_rules:
        print(timer.design_rule_limits())
    if args.design_rule_violations:
        for item in timer.design_rule_violations():
            print(item)
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
